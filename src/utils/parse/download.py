from typing import Callable

from utils.common.model.task_info import DownloadTaskInfo
from utils.common.enums import StreamType, VideoCodecID, AudioQualityID, ParseType
from utils.common.map import audio_file_type_map
from utils.common.exception import GlobalException

from utils.parse.preview import VideoPreview
from utils.parse.parser import Parser
from utils.parse.video import VideoParser

class DownloadParser(Parser):
    def __init__(self, task_info: DownloadTaskInfo, callback: Callable):
        super().__init__()

        self.callback = callback
        self.task_info = task_info

    @classmethod
    def get_download_stream_json(cls, task_info: DownloadTaskInfo):
        cls.get_extra_info(task_info)

        data = VideoPreview.get_download_json(task_info.parse_type, task_info.bvid, task_info.cid, task_info.aid, task_info.ep_id, task_info.video_quality_id)

        task_info.stream_type = VideoPreview.get_stream_type(data)

        return data

    def parse_download_stream_json(self, data: dict):
        match StreamType(self.task_info.stream_type):
            case StreamType.Dash:
                downloader_info = self.parse_dash_json(data)

            case StreamType.Flv:
                downloader_info = self.parse_flv_json(data)

            case StreamType.Mp4:
                downloader_info = self.parse_mp4_json(data)

        if None in downloader_info:
            downloader_info.remove(None)
        
        return downloader_info
    
    def parse_dash_json(self, data: dict):
        def get_download_items():
            if not self.task_info.download_items:
                self.task_info.download_items = self.task_info.download_option.copy()

                if self.task_info.download_option == ["video", "audio"] and not data["dash"]["audio"]:
                    self.task_info.download_items = ["video"]

        def get_output_type():
            match self.task_info.download_items:
                case ["audio"]:
                    self.task_info.output_type = self.task_info.audio_type

                case _:
                    self.task_info.output_type = "mp4"
        
        get_download_items()

        downloader_info = []

        if "video" in self.task_info.download_items:
            downloader_info.append(self.parse_video_stream(data))

        if "audio" in self.task_info.download_items:
            downloader_info.append(self.parse_audio_stream(data))

        get_output_type()

        return downloader_info

    def parse_flv_json(self, data: dict):
        def check_download_items():
            if not self.task_info.download_items:
                self.task_info.download_items = [f"flv_{index + 1}" for index in range(len(data["durl"]))]

        def get_flv_info():
            self.task_info.audio_quality_id = AudioQualityID._None.value
            self.task_info.download_option = ["video"]
            self.task_info.flv_video_count = len(data["durl"])
        
        check_download_items()

        get_flv_info()

        return self.parse_flv_stream(data)

    def parse_mp4_json(self, data: dict):
        def get_mp4_info():
            self.task_info.audio_quality_id = AudioQualityID._None.value
            self.task_info.download_option = ["video"]
            self.task_info.download_items = ["video"]

        get_mp4_info()

        return self.parse_mp4_stream(data)

    def parse_video_stream(self, data: list):
        self.task_info.video_type = "m4s"

        self.task_info.video_quality_id = VideoPreview.get_video_quality_id(self.task_info.video_quality_id, data)
        self.task_info.video_codec_id = VideoPreview.get_video_codec_id(self.task_info.video_quality_id, self.task_info.video_codec_id, self.task_info.stream_type, data)

        for entry in data["dash"]["video"]:
            if entry["id"] == self.task_info.video_quality_id and entry["codecid"] == self.task_info.video_codec_id:
                return {
                    "url_list": VideoPreview.get_stream_download_url_list(entry),
                    "file_name": f"video_{self.task_info.id}.m4s",
                    "type": "video"
                }

    def parse_audio_stream(self, data: dict):
        self.task_info.audio_quality_id = VideoPreview.get_audio_quality_id(self.task_info.audio_quality_id, data["dash"])
        self.task_info.audio_type = audio_file_type_map.get(self.task_info.audio_quality_id)

        all_url_list = VideoPreview.get_audio_all_url_list(data["dash"])

        for entry in all_url_list:
            if entry["id"] == self.task_info.audio_quality_id:
                return {
                    "url_list": VideoPreview.get_stream_download_url_list(entry),
                    "file_name": f"audio_{self.task_info.id}.{self.task_info.audio_type}",
                    "type": "audio"
                }
    
    def parse_flv_stream(self, data: dict):
        def get_flv_downloader_info(index: int):
            return {
                "url_list": url_list,
                "file_name": f"flv_{self.task_info.id}_part{index}.flv" if self.task_info.flv_video_count > 1 else f"flv_{self.task_info.id}.flv",
                "type": f"flv_{index}"
            }

        self.task_info.video_type = "flv"
        self.task_info.output_type = "flv"

        self.task_info.video_quality_id = VideoPreview.get_video_quality_id(self.task_info.video_quality_id, data)
        self.task_info.video_codec_id = VideoCodecID.AVC.value

        downloader_info = []

        for index, entry in enumerate(data["durl"]):
            if f"flv_{index + 1}" in self.task_info.download_items:
                url_list = VideoPreview.get_stream_download_url_list(entry)

                downloader_info.append(get_flv_downloader_info(index + 1))

        return downloader_info

    def parse_mp4_stream(self, data: dict):
        self.task_info.video_type = "mp4"
        self.task_info.output_type = "mp4"

        self.task_info.video_quality_id = VideoPreview.get_video_quality_id(self.task_info.video_quality_id, data)
        self.task_info.video_codec_id = VideoCodecID.AVC.value

        if data["durls"]:
            for entry in data["durls"]:
                if entry["quality"] == self.task_info.video_quality_id:
                    node = entry["durl"][0]
        else:
            node = data["durl"][0]

        url_list = VideoPreview.get_stream_download_url_list(node)

        return [
            {
                "url_list": url_list,
                "file_name": f"video_{self.task_info.id}.mp4",
                "type": "video"
            }
        ]

    def get_download_url(self):
        try:
            data = self.get_download_stream_json(self.task_info)

            return self.parse_download_stream_json(data)
        
        except Exception as e:
            raise GlobalException(callback = self.callback) from e

    @staticmethod
    def get_extra_info(task_info: DownloadTaskInfo):
        if ParseType(task_info.parse_type) == ParseType.Video:
            download_metadata = task_info.extra_option.get("download_metadata_file")

            if not task_info.cid:
                info = VideoParser.get_video_extra_info(task_info.bvid)

                task_info.cid = info.get("cid")

                task_info.up_name = info.get("up_name")
                task_info.up_uid = info.get("up_mid")

            if download_metadata:
                try:
                    info.get("up_face")
                except:
                    info = VideoParser.get_video_extra_info(task_info.bvid)

                task_info.up_face_url = info.get("up_face")
                task_info.description = info.get("description")
                task_info.video_tags = VideoParser.get_video_tags(task_info.bvid)