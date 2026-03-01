from util.common.enum import DownloadStatus, DownloadType
from util.download.cover.manager import cover_manager
from util.parse.episode.tree import EpisodeData
from util.common.timestamp import get_timestamp
from util.download.task.db import TaskDatabase
from util.common.signal_bus import signal_bus
from util.download.task.info import TaskInfo
from util.format import FileNameFormatter
from util.common.config import config

from pathlib import Path
from typing import List
from uuid import uuid4
import json

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
            DownloadType.DANMAKU: config.download_danmaku,
            DownloadType.SUBTITLE: config.download_subtitle,
            DownloadType.COVER: config.download_cover,
            DownloadType.METADATA: config.download_metadata
        }

        type = 0

        for attr, enabled in attr_dict.items():
            if enabled:
                type |= attr

        return type

    def __update_episode_info(self, episode_info: dict):
        extra_data = EpisodeData.get_episode_data(episode_info.get("episode_id", ""))

        return {
            **episode_info,
            **extra_data,
            **episode_info.get("related_titles", {})
        }

    def __update_file_name_info(self, task_info: TaskInfo):
        formatter = FileNameFormatter()
        formatter.set_variable_data(task_info)

        path = Path(formatter.format())

        task_info.File.name = str(path.name)
        task_info.File.download_path = config.get(config.download_path)
        task_info.File.folder = str(path.parent)

    def create(self, episode_info_list: List[dict]):
        task_info_list = []

        for episode_info in episode_info_list:
            task_info = self.__episode_info_to_task_info(episode_info)
            task_info_list.append(task_info)

        self.db_manager.add_tasks(task_info_list)

    def query(self, completed: bool = False) -> List[TaskInfo]:
        result = self.db_manager.query_tasks(completed)

        task_info_list = []

        for entry in result:
            data = entry[0]  # 获取 data 列

            task_info = TaskInfo()
            task_info.from_dict(json.loads(data))

            task_info_list.append(task_info)

        return task_info_list

task_manager = TaskManager()