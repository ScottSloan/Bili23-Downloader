from util.download.parse.query_worker import QueryWorker
from util.common.enum import MediaType, DownloadType
from util.common import config

from ...download.task.info import TaskInfo

from collections import defaultdict

class AudioInfoParser:
    def __init__(self, info_data: dict, task_info: TaskInfo):
        self.info_data = info_data
        self.task_info = task_info

        self.audio_quality_info_map = defaultdict(dict)

    def _get_dash_available_quality_list(self):
        available_quality_list = []

        dash_node = self.info_data["dash"]

        if audio_node := self.safe_get(dash_node.copy(), ["flac", "audio"]):
            quality_id = audio_node["id"]

            available_quality_list.append(quality_id)

            self.audio_quality_info_map[quality_id] = audio_node.copy()

        if audio_node := self.safe_get(dash_node.copy(), ["dolby", "audio"]):
            quality_id = audio_node[0]["id"]

            available_quality_list.append(quality_id)

            self.audio_quality_info_map[quality_id] = audio_node[0].copy()

        if dash_node.get("audio", []):

            for entry in dash_node["audio"].copy():
                quality_id = entry["id"]

                if quality_id not in available_quality_list:
                    available_quality_list.append(quality_id)

                    self.audio_quality_info_map[quality_id] = entry.copy()

        return available_quality_list

    def get_available_list(self):
        match self.task_info.Download.media_type:
            case MediaType.DASH:
                return self._get_dash_available_quality_list()
            
            case _:
                return []
    
    def parse_info(self):
        audio_info = self.get_audio_info(self.task_info.Download.audio_quality_id)

        if audio_info:
            self.task_info.Download.audio_quality_id = audio_info["id"]

            ext = self.get_audio_file_ext()

            temp_audio_file_name = "audio_{task_id}.{file_ext}".format(task_id = self.task_info.Basic.task_id, file_ext = ext)

            self.task_info.File.audio_file_ext = ext

            if temp_audio_file_name not in self.task_info.File.relative_files:
                self.task_info.File.relative_files.append(temp_audio_file_name)

            info = QueryWorker(audio_info)

            return [
                {
                    **info.query_dash_url(),
                    "type": "audio",
                    "file_name": temp_audio_file_name,
                    "file_key": "audio"
                }
            ]
        
        else:
            self.task_info.Download.type &= ~DownloadType.AUDIO
            return []

    def get_audio_info(self, audio_quality_id: int):
        self.get_available_list()

        if audio_quality_id == 30300:
            audio_info = self.get_audio_info_by_priority()
        else:
            audio_info = self.audio_quality_info_map.get(audio_quality_id, {})

        return audio_info

    def get_audio_info_by_priority(self):
        for quality_id in config.get(config.audio_quality_priority):
            if quality_id in self.audio_quality_info_map.keys():
                return self.audio_quality_info_map.get(quality_id, {})
            
    def get_audio_file_ext(self):
        match self.task_info.Download.audio_quality_id:
            case 30251:
                # Hi-Res 无损
                return "flac"
            
            case 30250:
                # 杜比全景声
                return "ec3"
            
            case _:
                return "m4a"

    def safe_get(self, data: dict, keys: list, default = None):
        for key in keys:
            if data := data.get(key):
                continue

            else:
                return default

        return data