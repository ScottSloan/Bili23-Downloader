import math
import time

from utils.auth.wbi import WbiUtils
from utils.config import Config

from utils.common.request import RequestUtils
from utils.common.model.data_type import ParseCallback
from utils.common.enums import StatusCode, ProcessingType

from utils.parse.parser import Parser
from utils.parse.episode_v2 import Episode
from utils.parse.video import VideoInfo, VideoParser

class SpaceInfo:
    mid: int = 0

    type: str = ""

    season_id: int = 0
    series_id: int = 0

    total: int = 0

    info_json: dict = {}

class SpaceParser(Parser):
    def __init__(self, callback: ParseCallback):
        super().__init__()

        self.callback = callback

    def get_mid(self, url: str):
        mid = self.re_find_str(r"/([0-9]+)/", url)

        SpaceInfo.mid = mid[0]

    def get_type(self, url: str):
        type = self.re_find_str(r"type=(\w+)", url)

        SpaceInfo.type = type[0]
    
    def get_season_series_id(self, url: str):
        id = self.re_find_str(r"/([0-9]+)\?type", url)

        setattr(SpaceInfo, f"{SpaceInfo.type}_id" , id[0])

        self.reset_info_json()

    def get_sid(self, url: str):
        sid = self.re_find_str(r"sid=([0-9]+)", url)

        SpaceInfo.series_id = sid[0]

        self.reset_info_json()

    def get_season_info(self, page_num: int = 1):
        params = {
            "mid": SpaceInfo.mid,
            "season_id": SpaceInfo.season_id,
            "page_num": page_num,
            "page_size": 30
        }

        url = f"https://api.bilibili.com/x/polymer/web-space/seasons_archives_list?{WbiUtils.encWbi(params)}"

        resp = self.request_get(url, headers = RequestUtils.get_headers(referer_url = self.bilibili_url, sessdata = Config.User.SESSDATA))

        SpaceInfo.total = resp["data"]["meta"]["total"]
        SpaceInfo.info_json["meta"]["title"] = resp["data"]["meta"]["name"]
        SpaceInfo.info_json["archives"].extend(resp["data"]["archives"])

    def get_series_meta_info(self):
        params = {
            "series_id": SpaceInfo.series_id,
        }

        url = f"https://api.bilibili.com/x/series/series?{self.url_encode(params)}"

        resp = self.request_get(url, headers = RequestUtils.get_headers(referer_url = self.bilibili_url, sessdata = Config.User.SESSDATA))

        SpaceInfo.total = resp["data"]["meta"]["total"]
        SpaceInfo.info_json["meta"]["title"] = resp["data"]["meta"]["name"]

    def get_series_archives_info(self, pn: int = 1):
        params = {
            "mid": SpaceInfo.mid,
            "series_id": SpaceInfo.series_id,
            "pn": pn,
            "ps": 30
        }

        url = f"https://api.bilibili.com/x/series/archives?{self.url_encode(params)}"

        resp = self.request_get(url, headers = RequestUtils.get_headers(referer_url = "https://www.bilibili.com"))

        SpaceInfo.info_json["archives"].extend(resp["data"]["archives"])

    def get_video_available_media_info(self):
        episode = SpaceInfo.info_json["archives"][0]

        VideoInfo.bvid = episode["bvid"]
        VideoInfo.cid = VideoParser.get_video_cid(episode["bvid"])

        VideoParser.get_video_available_media_info()

    def parse_worker(self, url: str):
        self.clear_space_info()

        self.get_mid(url)

        if "list" in url:
            if "type" in url:
                self.get_type(url)

                self.get_season_series_id(url)

                match SpaceInfo.type:
                    case "season":
                        self.parse_season_info()

                    case "series":
                        self.parse_series_info()
            else:
                self.get_sid(url)

                self.parse_series_info()

        self.parse_episodes()

        self.get_video_available_media_info()

        return StatusCode.Success.value

    def parse_season_info(self):
        self.get_season_info()

        self.callback.onChangeProcessingType(ProcessingType.Page)

        for i in range(1, self.total_page):
            self.get_season_info(i + 1)

            self.update_loop(i + 1)

    def parse_series_info(self):
        self.get_series_meta_info()

        self.callback.onChangeProcessingType(ProcessingType.Page)

        for i in range(self.total_page):
            self.get_series_archives_info(i + 1)

            self.update_loop(i + 1)

    def parse_episodes(self):
        Episode.List.parse_episodes(SpaceInfo.info_json)

    def clear_space_info(self):
        SpaceInfo.mid = 0

        SpaceInfo.season_id = 0
        SpaceInfo.season_id = 0

        SpaceInfo.total = 0

        SpaceInfo.info_json.clear()

    def onUpdateTitle(self, page: int, total_page: int, total_data: int):
        self.callback.onUpdateTitle(f"当前第 {page} 页，共 {total_page} 页，已解析 {total_data} 条数据")

    def update_loop(self, page: int):
        self.onUpdateTitle(page, self.total_page, len(SpaceInfo.info_json.get("archives")))

        time.sleep(0.1)

    def reset_info_json(self):
        SpaceInfo.info_json = {
            "meta": {
                "title": ""
            },
            "archives": []
        }

    @property
    def total_page(self):
        return math.ceil(SpaceInfo.total / 30)