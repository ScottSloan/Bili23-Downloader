from ...common.data import reversed_video_quality_map, reversed_audio_quality_map, video_codec_str_map
from ...common.enum import DownloadStatus, DownloadType, NumberingType, DuplicateDownloadResolution
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

from threading import Event
from pathlib import Path
from typing import List
from uuid import uuid4
import logging
import hashlib
import re

logger = logging.getLogger(__name__)

class TaskManager:
    def __init__(self):
        self.db_manager = TaskDatabase()

        signal_bus.download.create_task.connect(self._create_async)

    def _create_async(self, episode_info_list: List[dict]):
        GlobalThreadPoolTask.run_func(self.create, episode_info_list)

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

    def __check_reparse_needed(self, episode_info: dict):
        if episode_info.get("attribute", 0) & Attribute.NEED_PARSE_BIT:
            worker = ReparseWorker(episode_info)
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

    def create(self, episode_info_list: List[dict]):
        task_info_list = []

        for episode_info in episode_info_list:
            # 判断是否需要重新解析
            if self.__check_reparse_needed(episode_info):
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

        if task_info_list:
            # 存储到数据库，并添加到下载列表
            self.db_manager.add_tasks(task_info_list)

            signal_bus.download.add_to_downloading_list.emit(task_info_list)
            signal_bus.download.auto_manage_concurrent_downloads.emit()

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
        self.db_manager.update_task(task_info)

    def delete(self, task_info: TaskInfo, completed: bool = False):
        self.db_manager.delete_task(task_info.Basic.task_id, completed)

    def cancel(self, task_info: TaskInfo):
        signal_bus.download.remove_from_downloading_list.emit(task_info)

        self.delete(task_info)
        
        self._removeTemporaryFiles(task_info)

    def mark_as_completed(self, task_info: TaskInfo):
        self.delete(task_info)

        self.db_manager.add_tasks([task_info], completed = True)

    def reset(self, task_info: TaskInfo):
        # 重置下载状态为初始状态，适用于完全重新下载的场景
        task_info.Download.status = DownloadStatus.QUEUED

        task_info.Download.queue = []
        task_info.Download.files = {}
        task_info.Download.progress = 0
        task_info.Download.total_size = 0
        task_info.Download.downloaded_size = 0
        task_info.Download.speed = 0

        self._removeTemporaryFiles(task_info)

    def recreate(self, task_info: TaskInfo):
        self.db_manager.delete_task(task_info.Basic.task_id, completed = True)
        self.db_manager.add_tasks([task_info])

        signal_bus.download.add_to_downloading_list.emit([task_info])
        signal_bus.download.auto_manage_concurrent_downloads.emit()

    def _removeTemporaryFiles(self, task_info: TaskInfo):
        # 删除下载的临时文件
        safe_remove(Path(task_info.File.download_path, task_info.File.folder), *task_info.File.relative_files)

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

        return hashlib.md5(json_dumps(metadata).encode("utf-8")).hexdigest()
    
task_manager = TaskManager()
