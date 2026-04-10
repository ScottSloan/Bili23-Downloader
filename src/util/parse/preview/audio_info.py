from util.common.data import audio_reorder_map, reversed_audio_quality_map
from util.parse.preview.worker import QueryInfoWorker
from util.parse.preview.info import PreviewerInfo
from util.common import signal_bus, config
from util.common.enum import MediaType
from util.thread import AsyncTask

from collections import defaultdict
from typing import Callable

class AudioInfoParser:
    def __init__(self):
        self.callback: Callable = None
        self.audio_quality_info_map = {}

        signal_bus.parse.query_audio_info.connect(self.query_info)

    def _get_dash_available_quality_list(self):
        available_quality_list = []

        dash_node = PreviewerInfo.info_data["dash"]

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

        return sorted(available_quality_list, key = lambda x: audio_reorder_map.get(x))

    def get_available_list(self):
        match PreviewerInfo.media_type:
            case MediaType.DASH:
                return self._get_dash_available_quality_list()
            
            case _:
                return []
    
    def parse_info(self):
        self.audio_quality_info_map = defaultdict(dict)

        initial_data = {
            "auto": 30300
        }

        available_audio_quality = self.get_available_list()

        for quality_id in available_audio_quality.copy():
            quality_str = reversed_audio_quality_map.get(quality_id)

            initial_data[quality_str] = quality_id

        PreviewerInfo.audio_quality_choice_data = initial_data.copy()

    def query_info(self, audio_quality_id: int, callback: Callable):
        self.callback = callback

        audio_info = self.get_audio_info(audio_quality_id)

        if audio_info:
            quality_id = audio_info["id"]

            if cached_info := PreviewerInfo.cache["audio"][quality_id]:
                self.callback(cached_info)

            else:
                if "size" in audio_info.keys():
                    # 如果已有文件大小无需再 HEAD 请求
                    file_size = audio_info["size"]

                    self.on_query_info_success(audio_info, file_size)
                else:
                    worker = QueryInfoWorker(audio_info)
                    worker.success.connect(self.on_query_info_success)
                    worker.error.connect(lambda error: self.callback(None))

                    AsyncTask.run(worker)
                
        else:
            self.callback(None)

    def on_query_info_success(self, media_info: dict, file_size: int):
        quality_id = media_info["id"]

        info = {
            "quality_id": quality_id,
            "file_size": file_size,
            "bitrate": media_info["bandwidth"],
            "codec": media_info["codecs"]
        }

        if quality_id not in PreviewerInfo.cache["audio"]:
            PreviewerInfo.cache["audio"][quality_id] = info.copy()

        self.callback(info)

    def get_audio_info(self, audio_quality_id: int):
        if audio_quality_id == 30300:
            return self.get_audio_info_by_priority()

        else:
            return self.audio_quality_info_map.get(audio_quality_id, {})

    def get_audio_info_by_priority(self):
        for quality_id in config.get(config.audio_quality_priority):
            if quality_id in self.audio_quality_info_map.keys():
                return self.audio_quality_info_map.get(quality_id, {})

    def make_empty_data(self, reason: str):
        return {
            "empty": True,
            "reason": reason
        }

    def safe_get(self, data: dict, keys: list, default = None):
        for key in keys:
            if data := data.get(key):
                continue

            else:
                return default

        return data
