from util.common.data import reversed_video_quality_map, reversed_audio_quality_map, video_codec_str_map
from util.common import signal_bus, config, safe_remove, get_timestamp_ms, Translator
from util.parse.episode.tree import EpisodeData, Attribute
from util.common.enum import DownloadStatus, DownloadType
from util.thread import GlobalThreadPoolTask
from util.format import FileNameFormatter

from ..cover.manager import cover_manager
from .reparse_worker import ReparseWorker
from .db import TaskDatabase
from .info import TaskInfo

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

    def create(self, episode_info_list: List[dict]):
        task_info_list = []

        for episode_info in episode_info_list:
            if self.__check_reparse_needed(episode_info):
                continue

            task_info = self.__episode_info_to_task_info(episode_info)

            task_info_list.append(task_info)

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
            task_info.from_dict(json.loads(data))

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

task_manager = TaskManager()

