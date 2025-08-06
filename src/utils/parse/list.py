from utils.common.request import RequestUtils
from utils.common.enums import StatusCode
from utils.common.model.data_type import ParseCallback

from utils.parse.parser import Parser
from utils.parse.video import VideoInfo, VideoParser
from utils.parse.episode_v2 import Episode

class ListInfo:
    mid: int = 0
    series_id: int = 0

    info_json: int = {}

class ListParser(Parser):
    def __init__(self, callback: ParseCallback):
        super().__init__()

        self.callback = callback

    def get_mid(self, url: str):
        mid = self.re_find_str(r"list/([0-9]+)/", url)

        ListInfo.mid = mid[0]

    def get_series_id(self, url: str):
        series_id = self.re_find_str(r"sid=([0-9]+)", url)

        ListInfo.series_id = series_id[0]

    def get_series_info(self):
        self.get_series_archives()
        self.get_series_meta()

        self.parse_episodes()

    def get_series_meta(self):
        params = {
            "series_id": ListInfo.series_id
        }

        url = f"https://api.bilibili.com/x/series/series?{self.url_encode(params)}"

        resp = self.request_get(url, headers = RequestUtils.get_headers(referer_url = "https://www.bilibili.com"))

        ListInfo.info_json["meta"] = {
            "title": resp["data"]["meta"]["name"]
        }

    def get_series_archives(self):
        params = {
            "mid": ListInfo.mid,
            "series_id": ListInfo.series_id,
            "pn": 1,
            "ps": 20
        }

        url = f"https://api.bilibili.com/x/series/archives?{self.url_encode(params)}"

        resp = self.request_get(url, headers = RequestUtils.get_headers(referer_url = "https://www.bilibili.com"))

        ListInfo.info_json = resp["data"].copy()

    def get_list_available_media_info(self):
        episode = ListInfo.info_json["archives"][0]

        VideoInfo.bvid = episode["bvid"]
        VideoInfo.cid = VideoParser.get_video_cid(episode["bvid"])

        VideoParser.get_video_available_media_info()

    def parse_worker(self, url):
        self.get_mid(url)
        self.get_series_id(url)

        self.get_series_info()

        self.get_list_available_media_info()

        return StatusCode.Success.value
    
    def parse_episodes(self):
        Episode.List.parse_episodes(ListInfo.info_json)