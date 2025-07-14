import json
from typing import Callable

from utils.common.data_type import DownloadTaskInfo, DownloaderInfo
from utils.common.enums import ParseType, StreamType, VideoQualityID, VideoCodecID, AudioQualityID
from utils.common.map import audio_file_type_map
from utils.common.exception import GlobalException
from utils.common.request import RequestUtils

from utils.parse.preview import Preview
from utils.parse.parser import Parser
from utils.parse.audio import AudioInfo

from utils.auth.wbi import WbiUtils
from utils.config import Config

class DownloadParser(Parser):
    def __init__(self, task_info: DownloadTaskInfo, callback: Callable):
        super().__init__()

        self.callback = callback
        self.task_info = task_info

    @classmethod
    def get_download_stream_json(cls, task_info: DownloadTaskInfo):
        def check_stream_type(data: dict):
            if "dash" in data:
                task_info.stream_type = StreamType.Dash.value
                
            elif "durl" in data:
                task_info.stream_type = StreamType.Flv.value

            return data

        def get_video_json():
            params = {
                "bvid": task_info.bvid,
                "cid": task_info.cid,
                "fnver": 0,
                "fnval": 4048,
                "fourk": 1
            }

            url = f"https://api.bilibili.com/x/player/wbi/playurl?{WbiUtils.encWbi(params)}"

            req = RequestUtils.request_get(url, headers = RequestUtils.get_headers(referer_url = task_info.referer_url, sessdata = Config.User.SESSDATA))
            data = json.loads(req.text)

            cls.check_json(cls, data)

            return check_stream_type(data["data"])

        def get_bangumi_json():
            url = f"https://api.bilibili.com/pgc/player/web/playurl?bvid={task_info.bvid}&cid={task_info.cid}&qn={task_info.video_quality_id}&fnver=0&fnval=12240&fourk=1"

            req = RequestUtils.request_get(url, headers = RequestUtils.get_headers(referer_url = task_info.referer_url, sessdata = Config.User.SESSDATA))
            data = json.loads(req.text)

            cls.check_json(cls, data)

            return check_stream_type(data["result"])

        def get_cheese_json():
            url = f"https://api.bilibili.com/pugv/player/web/playurl?avid={task_info.aid}&ep_id={task_info.ep_id}&cid={task_info.cid}&fnver=0&fnval=4048&fourk=1"

            req = RequestUtils.request_get(url, headers = RequestUtils.get_headers(referer_url = task_info.referer_url, sessdata = Config.User.SESSDATA))
            data = json.loads(req.text)

            cls.check_json(cls, data)

            return check_stream_type(data["data"])

        match ParseType(task_info.parse_type):
            case ParseType.Video:
                return get_video_json()

            case ParseType.Bangumi:
                return get_bangumi_json()

            case ParseType.Cheese:
                return get_cheese_json()

    def parse_download_stream_json(self, data: dict):
        if self.task_info.stream_type == StreamType.Dash.value:
            downloader_info = self.parse_dash_json(data)

        else:
            downloader_info = self.parse_flv_json(data)

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

    def parse_video_stream(self, data: list):
        def get_video_downloader_info(entry: dict):
            info = DownloaderInfo()
            info.url_list = Preview.get_stream_download_url_list(entry)
            info.type = "video"
            info.file_name = f"video_{self.task_info.id}.m4s"

            return info.to_dict()
        
        self.task_info.video_type = "m4s"

        self.task_info.video_quality_id = Preview.get_video_quality_id(self.task_info.video_quality_id, data)
        self.task_info.video_codec_id = Preview.get_video_codec_id(self.task_info.video_quality_id, self.task_info.video_codec_id, self.task_info.stream_type, data)

        for entry in data["dash"]["video"]:
            if entry["id"] == self.task_info.video_quality_id and entry["codecid"] == self.task_info.video_codec_id:
                return get_video_downloader_info(entry)
            
        return get_video_downloader_info()

    def parse_audio_stream(self, data: dict):
        def get_audio_downloader_info(entry: dict):
            info = DownloaderInfo()
            info.url_list = Preview.get_stream_download_url_list(entry)
            info.type = "audio"
            info.file_name = f"audio_{self.task_info.id}.{self.task_info.audio_type}"

            return info.to_dict()

        self.task_info.audio_quality_id = Preview.get_audio_quality_id(self.task_info.audio_quality_id, data["dash"])

        self.task_info.audio_type = audio_file_type_map.get(self.task_info.audio_quality_id)

        all_url_list = AudioInfo.get_all_audio_url_list(data["dash"])

        for entry in all_url_list:
            if entry["id"] == self.task_info.audio_quality_id:
                return get_audio_downloader_info(entry)
    
    def parse_flv_stream(self, data: dict):
        def get_flv_quality_id():
            highest_video_quality_id = data["accept_quality"][0]

            if self.task_info.video_quality_id == VideoQualityID._Auto.value:
                self.task_info.video_quality_id = highest_video_quality_id

            elif highest_video_quality_id < self.task_info.video_quality_id:
                self.task_info.video_quality_id = highest_video_quality_id
        
        def get_flv_downloader_info(index: int):
            if url_list:
                info = DownloaderInfo()
                info.url_list = url_list
                info.type = f"flv_{index}"

                if self.task_info.flv_video_count > 1:
                    info.file_name = f"flv_{self.task_info.id}_part{index}.flv"
                else:
                    info.file_name = f"flv_{self.task_info.id}.flv"

                return info.to_dict()
            else:
                return None

        self.task_info.video_type = "flv"
        self.task_info.output_type = "flv"
        self.task_info.video_codec_id = VideoCodecID.AVC.value

        get_flv_quality_id()

        downloader_info = []

        for index, entry in enumerate(data["durl"]):
            if f"flv_{index + 1}" in self.task_info.download_items:
                url_list = Preview.get_stream_download_url_list(entry)

                downloader_info.append(get_flv_downloader_info(index + 1))

        return downloader_info

    def get_download_url(self):
        try:
            data = self.get_download_stream_json(self.task_info)

            return self.parse_download_stream_json(data)
        
        except Exception as e:
            raise GlobalException(callback = self.callback) from e
