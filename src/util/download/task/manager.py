from ...common.enum import DownloadStatus, DownloadType, NumberingType, DuplicateDownloadResolution, ToastNotificationCategory
from ...common.data import reversed_video_quality_map, reversed_audio_quality_map, video_codec_str_map
from ...common._json import json_dumps, json_loads
from ...common.timestamp import get_timestamp_ms
from ...common.translator import Translator
from ...common.signal_bus import signal_bus
from ...common.io.file import safe_remove
from ...common.config import config

from ...parse.episode.tree import EpisodeData, Attribute
from ...format.file_name import FileNameFormatter
from ...thread.pool import GlobalThreadPoolTask

from ..cover.manager import cover_manager
from .reparse_worker import ReparseWorker
from .db import TaskDatabase
from .info import TaskInfo

from threading import Event, Lock, Timer
from pathlib import Path
from typing import List
from uuid import uuid4
from concurrent.futures import ThreadPoolExecutor
import logging
import hashlib
import re

logger = logging.getLogger(__name__)

class TaskManager:
    def __init__(self):
        self.db_manager = TaskDatabase()
        self._add_to_queue_toast_shown = False
        self._add_to_queue_toast_lock = Lock()
        self._update_lock = Lock()
        self._pending_updates = {}
        self._update_flush_scheduled = False
        # 所有对 task.db 的写入都在这一个线程上串行执行：既保证了顺序，
        # 也避免了 GUI 线程与写线程争抢 SQLite 写锁。
        self._update_executor = ThreadPoolExecutor(max_workers = 1, thread_name_prefix = "task-db")
        # 删除临时文件可能涉及大量磁盘操作，与数据库写入互不依赖，单独放一个线程执行。
        self._cancel_executor = ThreadPoolExecutor(max_workers = 1, thread_name_prefix = "task-cancel")

        signal_bus.download.create_task.connect(self._create_async)

    def _create_async(self, episode_info_list: List[dict], show_toast: bool = False):
        GlobalThreadPoolTask.run_func(self.create, episode_info_list, show_toast)

    def _show_add_to_queue_toast(self):
        with self._add_to_queue_toast_lock:
            if self._add_to_queue_toast_shown:
                return

            self._add_to_queue_toast_shown = True

        signal_bus.toast.show.emit(
            ToastNotificationCategory.SUCCESS,
            "",
            Translator.TIP_MESSAGES("ADDED_TO_DOWNLOAD_QUEUE")
        )

        timer = Timer(3, self._reset_add_to_queue_toast_flag)
        timer.daemon = True
        timer.start()

    def _reset_add_to_queue_toast_flag(self):
        with self._add_to_queue_toast_lock:
            self._add_to_queue_toast_shown = False

    def __episode_info_to_task_info(self, episode_info: dict, number) -> TaskInfo:
        task_info = TaskInfo()

        # BasicInfo
        task_info.Basic.task_id = str(uuid4())
        task_info.Basic.cover_id = cover_manager.arrange_cover_id(episode_info.get("cover", ""))
        task_info.Basic.show_title = episode_info.get("title", "")
        task_info.Basic.created_time = get_timestamp_ms()
        
        # DownloadInfo
        task_info.Download.status = DownloadStatus.QUEUED
        task_info.Download.type = self.__determine_download_type()

        task_info.Download.video_quality_id = config.video_quality_id
        task_info.Download.audio_quality_id = config.audio_quality_id
        task_info.Download.video_codec_id = config.video_codec_id
        task_info.Download.merge_video_audio = config.merge_video_audio
        task_info.Download.keep_original_files = config.keep_original_files

        # EpisodeInfo
        task_info.Episode.from_dict(self.__update_episode_info(episode_info, number))

        # FileNameInfo
        # 下载目录在生成 TaskInfo 时就确定，后续即便修改了下载目录的设置，也不会影响已生成的 TaskInfo 中的下载目录，避免下载过程中下载目录发生变化导致的问题
        task_info.File.download_path = config.get(config.download_path)

        self.__update_file_name_info(task_info)

        return task_info

    def __determine_download_type(self):
        # 确定下载类型
        attr_dict = {
            DownloadType.VIDEO: config.download_video_stream,
            DownloadType.AUDIO: config.download_audio_stream,
            DownloadType.DANMAKU: config.get(config.download_danmaku),
            DownloadType.SUBTITLE: config.get(config.download_subtitle),
            DownloadType.COVER: config.get(config.download_cover),
            DownloadType.METADATA: config.get(config.download_metadata)
        }

        type = 0

        for attr, enabled in attr_dict.items():
            if enabled:
                type |= attr

        return type

    def __update_episode_info(self, episode_info: dict, number):
        extra_data = EpisodeData.get_episode_data(episode_info.get("episode_id", ""))

        title = episode_info.get("title", "")
        attr = episode_info.get("attribute", 0)

        # 对于任何类型视频，都保存一个 leaf_title 备用，供下载收藏夹和个人空间时使用
        episode_info["leaf_title"] = title

        # 对于剧集和课程，使用 episode_title 表示剧集名称或课程名称，leaf_title 表示分P标题
        if attr & Attribute.BANGUMI_BIT != 0 or attr & Attribute.CHEESE_BIT != 0:
            episode_info["episode_title"] = title

        data = {
            **episode_info,
            **extra_data,
            **episode_info.get("related_titles", {}),
            **episode_info.get("uploader_info", {}),
            "number": number
        }

        # 过滤文件系统非法字符
        self.__filter_illegal_characters(data)

        return data

    def __update_file_name_info(self, task_info: TaskInfo):
        formatter = FileNameFormatter()
        formatter.set_variable_data(task_info)

        if config.target_naming_rule_id is not None:
            formatter.set_rule(formatter.get_rule_by_id(config.target_naming_rule_id))

        path = Path(formatter.format())

        task_info.File.name = str(path.name)
        task_info.File.folder = str(path.parent)

    def __check_reparse_needed(self, episode_info: dict, show_toast: bool = False):
        if episode_info.get("attribute", 0) & Attribute.NEED_PARSE_BIT:
            worker = ReparseWorker(episode_info, show_toast)
            GlobalThreadPoolTask.run(worker)

            return True
        
        return False

    def __filter_illegal_characters(self, episode_info: dict):
        title_list = [
            "leaf_title", 
            "parent_title",
            "section_title",
            "collection_title",
            "series_title",
            "season_title",
            "episode_title",
            "favorites_owner",
            "space_owner"
        ]

        for title in title_list:
            if title in episode_info:
                # 过滤文件系统非法字符
                episode_info[title] = re.sub(r'[\/\\\:\*\?\"\<\>\|]', '_', episode_info.get(title, ""))

    def __get_number(self, episode_info: dict = None):
        match config.get(config.numbering_type):
            case NumberingType.CONTINUOUS:
                # 全局顺序编号
                return config.global_starting_number
            
            case NumberingType.FROM_SPECIFIED:
                # 返回 current_starting_number，然后自增
                _current = config.current_starting_number
                config.current_starting_number += 1

                return _current
            
            case _:
                return episode_info.get("number", "")

    def create(self, episode_info_list: List[dict], show_toast: bool = False):
        task_info_list = []

        for episode_info in episode_info_list:
            try:
                # 判断是否需要重新解析
                if self.__check_reparse_needed(episode_info, show_toast):
                    continue

                # 判断是否重复下载
                if self._check_duplicate(episode_info):
                    continue

                # 先判断重复下载，再分配编号
                number = self.__get_number(episode_info)

                task_info = self.__episode_info_to_task_info(episode_info, number)

                task_info_list.append(task_info)

                # 全局起始编号自增
                config.global_starting_number += 1

            except Exception as error:
                title = episode_info.get("title", "")
                logger.exception("创建下载任务失败：%s", title)

                signal_bus.toast.show_long_message.emit(
                    ToastNotificationCategory.ERROR,
                    Translator.ERROR_MESSAGES("DOWNLOAD_FAILED"),
                    f"{title}\n\n{error}"
                )

        if task_info_list:
            # 存储到数据库，并添加到下载列表
            try:
                self.db_manager.add_tasks(task_info_list)

            except Exception as error:
                logger.exception("保存下载任务失败")

                signal_bus.toast.show_long_message.emit(
                    ToastNotificationCategory.ERROR,
                    Translator.ERROR_MESSAGES("DOWNLOAD_FAILED"),
                    str(error)
                )

                return

            signal_bus.download.add_to_downloading_list.emit(task_info_list)
            signal_bus.download.auto_manage_concurrent_downloads.emit()

            if show_toast:
                self._show_add_to_queue_toast()

    def query(self, completed: bool = False) -> List[TaskInfo]:
        result = self.db_manager.query_tasks(completed)

        task_info_list = []

        for entry in result:
            data = entry[0]  # 获取 data 列

            task_info = TaskInfo()
            task_info.from_dict(json_loads(data))

            task_info_list.append(task_info)

        return task_info_list

    def update(self, task_info: TaskInfo):
        self.update_async(task_info)

    def update_async(self, task_info: TaskInfo):
        # 高频进度更新只保留每个任务最新快照，并由单独线程串行写入数据库。
        task_id = task_info.Basic.task_id
        data = json_dumps(task_info.to_dict())

        with self._update_lock:
            self._pending_updates[task_id] = (task_id, data)

            if self._update_flush_scheduled:
                return

            self._update_flush_scheduled = True

        self._update_executor.submit(self._flush_updates)

    def shutdown(self, timeout: float = 5.0):
        # 退出前把已投递的写入落盘。写入都在同一个线程上排队，
        # 因此只要等待队尾的任务完成即可，超时后不再继续阻塞退出流程。
        try:
            self._update_executor.submit(lambda: None).result(timeout = timeout)

        except Exception:
            logger.exception("等待下载任务写入完成超时")

    def _discard_pending_updates(self, task_id_list: List[str]):
        # 任务即将被删除，丢弃其尚未落盘的进度快照，避免无谓的写入
        with self._update_lock:
            for task_id in task_id_list:
                self._pending_updates.pop(task_id, None)

    def _flush_updates(self):
        while True:
            with self._update_lock:
                if not self._pending_updates:
                    self._update_flush_scheduled = False
                    return

                updates = list(self._pending_updates.values())
                self._pending_updates.clear()

            try:
                # 一次事务写入全部快照。逐条提交时每条约 18ms，批量提交后整批不到 1ms。
                self.db_manager.update_task_json_many(updates)

            except Exception:
                logger.exception("异步保存下载任务失败，本批共 %d 条", len(updates))

    def delete(self, task_info: TaskInfo, completed: bool = False):
        # 结构性操作与进度写入共用同一个写线程，天然保证先后顺序，
        # 无需再阻塞调用方等待挂起的写入完成。
        self.delete_many([task_info], completed)

    def delete_many(self, task_info_list: List[TaskInfo], completed: bool = False):
        if not task_info_list:
            return

        task_id_list = [task_info.Basic.task_id for task_info in task_info_list]

        self._discard_pending_updates(task_id_list)
        self._update_executor.submit(self._delete_storage, task_id_list, completed)

    def _delete_storage(self, task_id_list: List[str], completed: bool):
        try:
            self.db_manager.delete_tasks(task_id_list, completed)

        except Exception:
            logger.exception("删除下载任务记录失败，本批共 %d 条", len(task_id_list))

    def cancel(self, task_info: TaskInfo):
        self.cancel_async(task_info)

    def cancel_async(self, task_info: TaskInfo):
        self.cancel_many_async([task_info])

    def cancel_many_async(self, task_info_list: List[TaskInfo], notify: bool = True):
        if not task_info_list:
            return

        if notify:
            for task_info in task_info_list:
                signal_bus.download.remove_from_downloading_list.emit(task_info)

        self.delete_many(task_info_list)

        # 删除临时文件与数据库写入互不依赖，放到另一个线程并行处理
        self._remove_temporary_files_async(task_info_list)

    def _remove_temporary_files_async(self, task_info_list: List[TaskInfo]):
        # 在投递前就把待删除的文件列表快照下来，避免后台线程执行时读到已被改写的列表
        snapshots = [
            (
                task_info.Basic.task_id,
                Path(task_info.File.download_path, task_info.File.folder),
                list(task_info.File.relative_files)
            )
            for task_info in task_info_list
        ]

        self._cancel_executor.submit(self._remove_temporary_files_storage, snapshots)

    def _remove_temporary_files_storage(self, snapshots: List[tuple]):
        for task_id, directory, file_names in snapshots:
            if not file_names:
                continue

            try:
                safe_remove(directory, *file_names)

            except Exception:
                logger.exception("删除下载任务临时文件失败: %s", task_id)

    def mark_as_completed(self, task_info: TaskInfo):
        # 由 Merger 在 GUI 线程调用，改为投递到写线程，避免两次同步数据库写入阻塞界面。
        # 记录在调用方线程上组装，保证写入的是此刻的任务快照。
        self._discard_pending_updates([task_info.Basic.task_id])

        record = self.db_manager.build_record(task_info, completed = True)

        self._update_executor.submit(self._mark_as_completed_storage, record)

    def _mark_as_completed_storage(self, record: tuple):
        try:
            self.db_manager.move_to_completed(record)

        except Exception:
            logger.exception("标记下载任务为已完成失败: %s", record[0])

    def reset(self, task_info: TaskInfo):
        # 重置下载状态为初始状态，适用于完全重新下载的场景
        task_info.Download.status = DownloadStatus.QUEUED

        task_info.Download.queue = []
        task_info.Download.files = {}
        task_info.Download.progress = 0
        task_info.Download.total_size = 0
        task_info.Download.downloaded_size = 0
        task_info.Download.speed = 0

        # 临时文件删除放到后台线程，避免在 GUI 线程上做磁盘操作
        self._remove_temporary_files_async([task_info])

    def recreate(self, task_info: TaskInfo):
        self._discard_pending_updates([task_info.Basic.task_id])

        record = self.db_manager.build_record(task_info)

        self._update_executor.submit(self._recreate_storage, record)

        signal_bus.download.add_to_downloading_list.emit([task_info])
        signal_bus.download.auto_manage_concurrent_downloads.emit()

    def _recreate_storage(self, record: tuple):
        try:
            self.db_manager.recreate_task(record)

        except Exception:
            logger.exception("重建下载任务记录失败: %s", record[0])

    def _update_media_info(self, task_info: TaskInfo):
        # 更新媒体信息相关的变量，以便在文件命名规则中使用
        if task_info.Download.video_quality_id != 200:
            video_quality = reversed_video_quality_map.get(task_info.Download.video_quality_id, "")

            task_info.Episode.video_quality = Translator.VIDEO_QUALITY(video_quality)

        if task_info.Download.audio_quality_id != 30300:
            audio_quality = reversed_audio_quality_map.get(task_info.Download.audio_quality_id, "")

            task_info.Episode.audio_quality = Translator.AUDIO_QUALITY(audio_quality)

        if task_info.Download.video_codec_id != 20:
            video_codec = video_codec_str_map.get(task_info.Download.video_codec_id, "")

            task_info.Episode.video_codec = video_codec

        self.__update_file_name_info(task_info)

    def _check_duplicate(self, episode_info: dict):
        hash_id = self._calc_hash_id(episode_info)

        result = self.db_manager.check_duplicate(hash_id)

        if result:
            # 触发重复下载，根据用户设置执行相应的操作
            match config.get(config.duplicate_download_resolution):
                case DuplicateDownloadResolution.CONTINUE:
                    # 返回 False 表示继续下载
                    logger.info("已继续重复下载任务: %s", episode_info.get("title", ""))

                    return False

                case DuplicateDownloadResolution.SKIP:
                    # 返回 True 表示跳过下载
                    logger.info("已跳过重复下载任务: %s", episode_info.get("title", ""))

                    signal_bus.download.show_skip_duplicate_download_toast.emit(episode_info.get("title", ""))
                    
                    return True
                
                case DuplicateDownloadResolution.ALWAYS_ASK:
                    # 询问用户是否继续下载。后台线程等待主线程弹窗返回结果。
                    result_info = {"skip": True, "not_ask_again": False}
                    done_event = Event()

                    signal_bus.download.show_duplicate_download_dialog.emit(episode_info, result_info, done_event)
                    done_event.wait()

                    logger.info("用户选择%s重复下载任务: %s", "跳过" if result_info["skip"] else "继续", episode_info.get("title", ""))

                    return result_info["skip"]
                    
        return result

    def _calc_hash_id(self, episode_info: dict):
        # 根据 episode_info 计算 hash_id
        attr = episode_info.get("attribute", 0)

        if attr & Attribute.VIDEO_BIT:
            # 投稿视频
            metadata = {
                "bvid": episode_info.get("bvid"),
                "cid": episode_info.get("cid"),
                "aid": episode_info.get("aid")
            }

        elif attr & Attribute.BANGUMI_BIT:
            # 剧集类
            metadata = {
                "bvid": episode_info.get("bvid"),
                "cid": episode_info.get("cid"),
                "aid": episode_info.get("aid"),
                "ep_id": episode_info.get("ep_id")
            }

        elif attr & Attribute.CHEESE_BIT:
            # 课程类
            metadata = {
                "aid": episode_info.get("aid"),
                "cid": episode_info.get("cid"),
                "ep_id": episode_info.get("ep_id")
            }

        elif attr & Attribute.AUDIO_BIT:
            # 音乐类
            metadata = {
                "sid": episode_info.get("sid")
            }

        else:
            # 属性缺失或未知时同样要给出可区分的 hash，否则会抛出异常导致任务创建失败
            metadata = {
                "aid": episode_info.get("aid"),
                "bvid": episode_info.get("bvid"),
                "cid": episode_info.get("cid"),
                "ep_id": episode_info.get("ep_id"),
                "sid": episode_info.get("sid")
            }

        return hashlib.md5(json_dumps(metadata).encode("utf-8")).hexdigest()
    
task_manager = TaskManager()
