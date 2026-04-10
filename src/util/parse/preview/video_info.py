from util.common.data import reversed_video_quality_map
from util.parse.preview.worker import QueryInfoWorker
from util.parse.preview.info import PreviewerInfo
from util.common import signal_bus, config
from util.common.enum import MediaType
from util.thread import AsyncTask

from collections import defaultdict
from typing import Callable

class VideoInfoParser:
    def __init__(self):
        self.callback: Callable = None
        self.video_info_map = {}

        signal_bus.parse.query_video_info.connect(self.query_info)

    def _get_dash_available_quality_list(self):
        available_quality_list = set()

        for entry in PreviewerInfo.info_data["dash"]["video"].copy():
            quality_id = entry["id"]
            codec_id = entry["codecid"]

            self.video_info_map[quality_id][codec_id] = entry.copy()
            available_quality_list.add(quality_id)

        # 按从大到小的顺序排列清晰度
        return sorted(list(available_quality_list), reverse = True)
    
    def _get_mp4_available_quality_list(self):
        accept_quality_list = PreviewerInfo.info_data["accept_quality"].copy()
        
        for quality_id in accept_quality_list.copy():
            self.video_info_map[quality_id][7] = {
                "id": quality_id,
                "codecid": 7,
                "frame_rate": 0,
                "bandwidth": 0,
                "timelength": 0
            }

        return accept_quality_list

    def get_available_quality_list(self):
        match PreviewerInfo.media_type:
            case MediaType.DASH:
                return self._get_dash_available_quality_list()
            
            case MediaType.MP4 | MediaType.FLV:
                return self._get_mp4_available_quality_list()
            
            case MediaType.UNKNOWN:
                return []

    def get_available_codec_list(self, video_quality_id: int):
        return list(self.video_info_map[video_quality_id].keys())

    def parse_quality_info(self):
        self.video_info_map = defaultdict(lambda: defaultdict(dict))

        initial_data = {
            "auto": 200
        }

        self.available_quality_list = self.get_available_quality_list()

        for quality_id in self.available_quality_list.copy():
            quality_str = reversed_video_quality_map.get(quality_id)

            initial_data[quality_str] = quality_id
        
        PreviewerInfo.video_quality_choice_data = initial_data.copy()

    def parse_codec_info(self):
        initial_data = {
            "auto": 20,
            "AVC/H.264": 7,
            "HEVC/H.265": 12,
            "AV1": 13
        }

        PreviewerInfo.video_codec_choice_data = initial_data.copy()

    def query_info(self, video_quality_id: int, video_codec_id: int, callback: Callable):
        self.callback = callback

        video_info = self.get_video_info(video_quality_id, video_codec_id)

        if video_info:
            quality_id = video_info["id"]
            codec_id = video_info["codecid"]

            if cached_info := PreviewerInfo.cache["video"][quality_id][codec_id]:
                self.callback(cached_info)

            else:
                if "size" in video_info.keys():
                    # 如果已有文件大小无需再 HEAD 请求
                    file_size = video_info["size"]

                    self.on_query_info_success(video_info, file_size)
                else:
                    worker = QueryInfoWorker(video_info)
                    worker.success.connect(self.on_query_info_success)
                    worker.error.connect(lambda error: self.callback(None))

                    AsyncTask.run(worker)
        else:
            self.callback(None)

    def on_query_info_success(self, media_info: dict, file_size: int):
        quality_id = media_info["id"]
        codec_id = media_info["codecid"]

        info = {
            "quality_id": quality_id,
            "frame_rate": media_info["frame_rate"],
            "bitrate": media_info["bandwidth"],
            "file_size": file_size,
            "codec_id": codec_id,
            "is_full_video": self.check_is_full_video(media_info)
        }

        PreviewerInfo.cache["video"][quality_id][codec_id] = info.copy()

        self.callback(info)

    def get_video_info(self, video_quality_id: int, video_codec_id: int):
        if video_quality_id == 200:
            video_quality_id = self.get_video_quality_id_by_priority()

        elif video_quality_id not in self.available_quality_list:
            video_quality_id = self.available_quality_list[0]

        available_codec_list = self.get_available_codec_list(video_quality_id)

        if video_codec_id == 20:
            video_codec_id = self.get_video_codec_id_by_priority(video_quality_id)

        elif video_codec_id not in available_codec_list:
            video_codec_id = available_codec_list[0]

        return self.video_info_map[video_quality_id][video_codec_id]

    def get_video_quality_id_by_priority(self):
        for quality_id in config.get(config.video_quality_priority):
            if quality_id in self.video_info_map.keys():
                return quality_id
            
    def get_video_codec_id_by_priority(self, video_quality_id: int):
        for codec_id in config.get(config.video_codec_priority):
            if codec_id in self.video_info_map[video_quality_id].keys():
                return codec_id

    def check_is_full_video(self, media_info: dict):
        match PreviewerInfo.media_type:
            case MediaType.DASH:
                # dash 格式视频一定是完整的
                return True

            case MediaType.MP4 | MediaType.FLV:
                # 只需要检查 mp4 和 flv 格式
                return PreviewerInfo.info_data["timelength"] == media_info["timelength"]
