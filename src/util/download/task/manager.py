from util.common.data import reversed_video_quality_map, reversed_audio_quality_map, video_codec_str_map
from util.common import signal_bus, config, safe_remove, get_timestamp, Translator
from util.download.task.reparse_worker import ReparseWorker
from util.parse.episode.tree import EpisodeData, Attribute
from util.common.enum import DownloadStatus, DownloadType
from util.download.cover.manager import cover_manager
from util.download.task.db import TaskDatabase
from util.download.task.info import TaskInfo
from util.thread import GlobalThreadPoolTask
from util.format import FileNameFormatter


from pathlib import Path
from typing import List
from uuid import uuid4
import json
import re

class TaskManager:
    def __init__(self):
        self.db_manager = TaskDatabase()

        signal_bus.download.create_task.connect(self.create)

    def __episode_info_to_task_info(self, episode_info: dict) -> TaskInfo:
        task_info = TaskInfo()

        # BasicInfo
        task_info.Basic.task_id = str(uuid4())
        task_info.Basic.cover_id = cover_manager.arrange_cover_id(episode_info.get("cover", ""))
        task_info.Basic.show_title = episode_info.get("title", "")
        task_info.Basic.created_time = get_timestamp()
        
        # DownloadInfo
        task_info.Download.status = DownloadStatus.QUEUED
        task_info.Download.type = self.__determine_download_type()

        task_info.Download.video_quality_id = config.video_quality_id
        task_info.Download.audio_quality_id = config.audio_quality_id
        task_info.Download.video_codec_id = config.video_codec_id
        task_info.Download.merge_video_audio = config.merge_video_audio
        task_info.Download.keep_original_files = config.keep_original_files

        # EpisodeInfo
        task_info.Episode.from_dict(self.__update_episode_info(episode_info))

        # FileNameInfo
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

    def __update_episode_info(self, episode_info: dict):
        extra_data = EpisodeData.get_episode_data(episode_info.get("episode_id", ""))

        title = episode_info.get("title", "")

        attr = episode_info.get("attribute", 0)

        episode_info["leaf_title"] = title

        if attr & Attribute.BANGUMI_BIT != 0 or attr & Attribute.CHEESE_BIT != 0:
            episode_info["episode_title"] = title

        data = {
            **episode_info,
            **extra_data,
            **episode_info.get("related_titles", {}),
            **episode_info.get("uploader_info", {}),
            "number": self.__arrange_number()
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

        task_info.File.download_path = config.get(config.download_path)
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

    def __arrange_number(self):
        config.current_starting_number += 1

        return config.current_starting_number - 1

    def create(self, episode_info_list: List[dict], cookie_file: str = ""):
        task_info_list = []

        for episode_info in episode_info_list:
            if self.__check_reparse_needed(episode_info):
                continue

            task_info = self.__episode_info_to_task_info(episode_info)

            # 绑定 cookie 文件路径
            if cookie_file:
                task_info.cookie_file = cookie_file

            task_info_list.append(task_info)

        if task_info_list:
            # 存储到数据库，并添加到下载列表
            self.db_manager.add_tasks(task_info_list)

            signal_bus.download.add_to_downloading_list.emit(task_info_list)

    def query(self, completed: bool = False) -> List[TaskInfo]:
        result = self.db_manager.query_tasks(completed)

        task_info_list = []

        for entry in result:
            data = entry[0]  # 获取 data 列

            task_info = TaskInfo()
            task_info.from_dict(json.loads(data))

            task_info_list.append(task_info)

        return task_info_list

    def update(self, task_info: TaskInfo):
        self.db_manager.update_task(task_info)

    def delete(self, task_info: TaskInfo, completed: bool = False):
        self.db_manager.delete_task(task_info.Basic.task_id, completed)

    def cancel(self, task_info: TaskInfo):
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"取消任务: {task_info.Basic.task_id}")
        
        self.delete(task_info)
        
        self._removeTaskFiles(task_info)
        
        signal_bus.download.remove_from_downloading_list.emit(task_info)
        logger.info(f"任务取消完成")

    def mark_as_completed(self, task_info: TaskInfo):
        self.delete(task_info)

        self.db_manager.add_tasks([task_info], completed = True)

    def delete_completed(self, task_info: TaskInfo):
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"删除已完成任务: {task_info.Basic.task_id}")
        logger.info(f"下载路径: {task_info.File.download_path}")
        logger.info(f"文件夹: {task_info.File.folder}")
        logger.info(f"文件列表: {task_info.File.relative_files}")
        
        self.delete(task_info, completed=True)
        logger.info(f"数据库删除完成")
        
        self._removeTaskFiles(task_info)
        logger.info(f"本地文件删除完成")

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

    def _removeTaskFiles(self, task_info: TaskInfo):
        # 删除任务相关的所有文件（包括临时文件和已下载的文件）
        import logging
        import shutil
        logger = logging.getLogger(__name__)
        
        download_path = task_info.File.download_path
        folder = task_info.File.folder
        
        # 安全检查：folder 不能为空，防止误删整个下载目录
        if not folder:
            logger.warning(f"任务 {task_info.Basic.task_id} 的 folder 为空，跳过文件删除")
            return
        
        full_path = Path(download_path, folder)
        
        # 额外安全检查：确保路径在下载目录内
        if not str(full_path).startswith(str(download_path)):
            logger.error(f"任务 {task_info.Basic.task_id} 的路径异常，跳过文件删除: {full_path}")
            return
        
        if full_path.exists():
            try:
                # 删除任务文件夹内的所有文件
                for item in full_path.iterdir():
                    if item.is_file():
                        item.unlink(missing_ok=True)
                    elif item.is_dir():
                        shutil.rmtree(item, ignore_errors=True)
                
                # 尝试删除文件夹本身（如果为空）
                full_path.rmdir()
                logger.info(f"已删除任务文件夹: {full_path}")
            except Exception as e:
                logger.error(f"删除任务文件夹时出错: {e}")
                # 如果无法删除文件夹，至少删除已知文件
                safe_remove(full_path, *task_info.File.relative_files)
        else:
            logger.info(f"任务文件夹不存在: {full_path}")

    def _removeTemporaryFiles(self, task_info: TaskInfo):
        # 删除下载的临时文件（保留此方法以兼容旧代码）
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

task_manager = TaskManager()

