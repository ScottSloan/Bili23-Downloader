import json

from utils.common.data_type import DownloadTaskInfo, DownloaderInfo
from utils.common.enums import ParseType, StreamType, DownloadOption, VideoQualityID, VideoCodecID
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

                return data["durl"]

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
            return self.parse_dash_json(data)

        else:
            return self.parse_flv_json(data)

    def parse_dash_json(self, data: dict):
        downloader_info = []

        match DownloadOption(self.task_info.download_option):
            case DownloadOption.OnlyVideo:
                downloader_info.append(self.parse_video_stream(data["video"]))

            case DownloadOption.OnlyAudio:
                downloader_info.append(self.parse_audio_stream())

            case DownloadOption.VideoAndAudio:
                downloader_info.append(self.parse_video_stream(data["video"]))
                downloader_info.append(self.parse_audio_stream())

        return downloader_info

    def parse_flv_json(self, data: dict):
        pass

    def parse_video_stream(self, data: list):
        def get_highest_video_quality_id(data: list, dolby: bool = False):
            highest_video_quality_id = VideoQualityID._360P.value

            for entry in data:
                # 遍历列表，选取其中最高的清晰度
                if entry["id"] == VideoQualityID._Dolby_Vision.value and not dolby:
                    continue

                if entry["id"] > highest_video_quality_id:
                    highest_video_quality_id = entry["id"]

            return highest_video_quality_id

        def get_video_quality_id(data: list):
            highest_video_quality_id = get_highest_video_quality_id(data, dolby = Config.Download.enable_dolby)

            if self.task_info.video_quality_id == VideoQualityID._Auto.value:
                self.task_info.video_quality_id = highest_video_quality_id

            elif highest_video_quality_id < self.task_info.video_quality_id:
                # 当视频不存在选取的清晰度时，选取最高可用的清晰度
                self.task_info.video_quality_id = highest_video_quality_id

        def get_video_codec_id(data: list):
            def check_codec_id():
                codec_id_list = set()

                for entry in data:
                    if entry["id"] == self.task_info.video_quality_id:
                        codec_id_list.add(entry["codecid"])

                return list(codec_id_list)

            codec_id_list = check_codec_id()

            if self.task_info.video_codec_id not in codec_id_list:
                self.task_info.video_codec_id = VideoCodecID.AVC.value

        def get_video_downloader_info():
            info = DownloaderInfo()
            info.url_list = url_list
            info.type = "video"
            info.file_name = f"video_{self.task_info.id}.m4s"

            return info.to_dict()

        get_video_quality_id(data)

        get_video_codec_id(data)

        for entry in data:
            if entry["id"] == self.task_info.video_quality_id and entry["codecid"] == self.task_info.video_codec_id:
                url_list = self.get_stream_download_url_list(entry)

        return get_video_downloader_info()

    def parse_audio_stream(self):
        pass
    
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

        downloader_info = self.parse_download_stream_json(data)

        print(downloader_info)