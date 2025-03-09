import json

from utils.common.data_type import DownloadTaskInfo, DownloaderInfo
from utils.common.enums import ParseType, StreamType, DownloadOption, VideoQualityID, VideoCodecID, AudioQualityID
from utils.auth.wbi import WbiUtils
from utils.tool_v2 import RequestTool
from utils.config import Config

class DownloadParser:
    def __init__(self, task_info: DownloadTaskInfo):
        self.task_info = task_info

    def get_download_stream_json(self):
        def check_stream_type(data: dict):
            if "dash" in data:
                self.task_info.stream_type = StreamType.Dash.value

                return data["dash"]
                
            elif "durl" in data:
                self.task_info.stream_type = StreamType.Flv.value

                return data

        def get_video_json():
            params = {
                "bvid": self.task_info.bvid,
                "cid": self.task_info.cid,
                "fnver": 0,
                "fnval": 4048,
                "fourk": 1
            }

            url = f"https://api.bilibili.com/x/player/wbi/playurl?{WbiUtils.encWbi(params)}"

            req = RequestTool.request_get(url, headers = RequestTool.get_headers(referer_url = self.task_info.referer_url, sessdata = Config.User.SESSDATA))
            data = json.loads(req.text)

            return check_stream_type(data["data"])

        def get_bangumi_json():
            url = f"https://api.bilibili.com/pgc/player/web/playurl?bvid={self.task_info.bvid}&cid={self.task_info.cid}&qn={self.task_info.video_quality_id}&fnver=0&fnval=12240&fourk=1"

            req = RequestTool.request_get(url, headers = RequestTool.get_headers(referer_url = self.task_info.referer_url, sessdata = Config.User.SESSDATA))
            data = json.loads(req.text)

            return check_stream_type(data["result"])

        def get_cheese_json():
            url = f"https://api.bilibili.com/pugv/player/web/playurl?avid={self.task_info.aid}&ep_id={self.task_info.ep_id}&cid={self.task_info.cid}&fnver=0&fnval=4048&fourk=1"

            req = RequestTool.request_get(url, headers = RequestTool.get_headers(referer_url = self.task_info.referer_url, sessdata = Config.User.SESSDATA))
            data = json.loads(req.text)

            return check_stream_type(data["data"])

        match ParseType(self.task_info.download_type):
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
        def check_download_items():
            if not self.task_info.download_items:
                match DownloadOption(self.task_info.download_option):
                    case DownloadOption.OnlyVideo:
                        self.task_info.download_items = ["video"]

                    case DownloadOption.OnlyAudio:
                        self.task_info.download_items = ["audio"]

                    case DownloadOption.VideoAndAudio:
                        if "audio" in data:
                            self.task_info.download_items = ["video", "audio"]
                        else:
                            self.task_info.download_items = ["video"]
                            self.task_info.download_option = DownloadOption.OnlyVideo
                            self.task_info.merge_video_and_audio = False
        
        check_download_items()

        downloader_info = []

        if "video" in self.task_info.download_items:
            downloader_info.append(self.parse_video_stream(data["video"]))

        if "audio" in self.task_info.download_items:
            downloader_info.append(self.parse_audio_stream(data))

        return downloader_info

    def parse_flv_json(self, data: dict):
        def check_download_items():
            if not self.task_info.download_items:
                self.task_info.download_items = [f"flv_{index + 1}" for index in range(len(data["durl"]))]

        def get_flv_info():
            self.task_info.audio_quality_id = AudioQualityID._None.value
            self.task_info.download_option = DownloadOption.OnlyVideo.value
            self.task_info.merge_video_and_audio = False
            self.task_info.flv_video_count = len(data["durl"])
        
        check_download_items()

        get_flv_info()

        return self.parse_flv_stream(data)

    def parse_video_stream(self, data: list):
        def get_video_quality_id(data: list):
            def get_highest_video_quality_id(data: list, dolby: bool = False):
                highest_video_quality_id = VideoQualityID._360P.value

                for entry in data:
                    # 遍历列表，选取其中最高的清晰度
                    if entry["id"] == VideoQualityID._Dolby_Vision.value and not dolby:
                        continue

                    if entry["id"] > highest_video_quality_id:
                        highest_video_quality_id = entry["id"]

                return highest_video_quality_id

            highest_video_quality_id = get_highest_video_quality_id(data, dolby = Config.Download.enable_dolby)

            if self.task_info.video_quality_id == VideoQualityID._Auto.value:
                self.task_info.video_quality_id = highest_video_quality_id

            elif highest_video_quality_id < self.task_info.video_quality_id:
                self.task_info.video_quality_id = highest_video_quality_id

        def get_video_codec_id(data: list):
            def check_codec_id():
                codec_id_list = []

                for entry in data:
                    if entry["id"] == self.task_info.video_quality_id:
                        codec_id_list.append(entry["codecid"])

                return codec_id_list

            codec_id_list = check_codec_id()

            if self.task_info.video_codec_id not in codec_id_list:
                self.task_info.video_codec_id = VideoCodecID.AVC.value

        def get_video_downloader_info():
            if url_list:
                info = DownloaderInfo()
                info.url_list = url_list
                info.type = "video"
                info.file_name = f"video_{self.task_info.id}.m4s"

                return info.to_dict()
            else:
                return None

        get_video_quality_id(data)

        get_video_codec_id(data)

        for entry in data:
            if entry["id"] == self.task_info.video_quality_id and entry["codecid"] == self.task_info.video_codec_id:
                url_list = self.get_stream_download_url_list(entry)

        return get_video_downloader_info()

    def parse_audio_stream(self, data: dict):
        def get_audio_quality_id(data: dict):
            def get_highest_audio_quality_id(data: dict, dolby: bool = False):
                highest_audio_quality = AudioQualityID._64K.value

                for entry in data["audio"]:
                    if entry["id"] > highest_audio_quality:
                        highest_audio_quality = entry["id"]

                if data["dolby"]:
                    if data["dolby"]["audio"] and dolby:
                        highest_audio_quality = AudioQualityID._Dolby_Atoms.value

                if data["flac"]:
                    if data["flac"]["audio"]:
                        highest_audio_quality = AudioQualityID._Hi_Res.value

                return highest_audio_quality
            
            highest_audio_quality = get_highest_audio_quality_id(data, dolby = Config.Download.enable_dolby)

            if self.task_info.audio_quality_id == AudioQualityID._Auto.value:
                self.task_info.audio_quality_id = highest_audio_quality

            elif highest_audio_quality < self.task_info.video_quality_id:
                self.task_info.video_quality_id = highest_audio_quality
            
        def get_audio_stream_url_list(data: dict):
            def get_hi_res():
                return self.get_stream_download_url_list(data["flac"]["audio"])

            def get_dolby():
                return self.get_stream_download_url_list(data["dolby"]["audio"])

            def get_normal():
                for entry in data["audio"]:
                    if entry["id"] == self.task_info.audio_quality_id:
                        return self.get_stream_download_url_list(entry)

            match AudioQualityID(self.task_info.audio_quality_id):
                case AudioQualityID._None:
                    return None

                case AudioQualityID._Hi_Res:
                    self.task_info.audio_type = "flac"
                    return get_hi_res()

                case AudioQualityID._Dolby_Atoms:
                    self.task_info.audio_type = "ec3"
                    return get_dolby()

                case _:
                    self.task_info.audio_type = "m4a"
                    return get_normal()

        def get_audio_downloader_info():
            if url_list:
                info = DownloaderInfo()
                info.url_list = url_list
                info.type = "audio"
                info.file_name = f"audio_{self.task_info.id}.{self.task_info.audio_type}"

                return info.to_dict()
            else:
                return None

        get_audio_quality_id(data)

        url_list = get_audio_stream_url_list(data)

        return get_audio_downloader_info()
    
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
                info.file_name = f"flv_{self.task_info.id}_part{index}.flv"

                return info.to_dict()
            else:
                return None

        get_flv_quality_id()

        downloader_info = []

        for index, entry in enumerate(data["durl"]):
            if f"flv_{index + 1}" in self.task_info.download_items:
                url_list = self.get_stream_download_url_list(entry)

                downloader_info.append(get_flv_downloader_info(index + 1))

        return downloader_info

    def get_stream_download_url_list(self, data: dict):
        def generator(x: list):
            for v in x:
                if isinstance(v, list):
                    for y in v:
                        yield y
                else:
                    yield v

        return [i for i in generator([data[n] for n in ["backupUrl", "backup_url", "baseUrl", "base_url", "url"] if n in data])]

    def get_download_url(self):
        data = self.get_download_stream_json()

        return self.parse_download_stream_json(data)