import math
import time
from typing import Dict

from utils.auth.wbi import WbiUtils
from utils.config import Config

from utils.common.request import RequestUtils
from utils.common.model.callback import ParseCallback
from utils.common.enums import StatusCode, ProcessingType

from utils.parse.parser import Parser
from utils.parse.episode_v2 import Episode

class SpaceListInfo:
    mid: int = 0

    type: str = ""

    season_id: int = 0
    series_id: int = 0

    total: int = 0

    info_json: dict = {}

class Section:
    info_json: Dict[str, Dict[str, Dict[str, list]]] = {
        "archives": {}
    }
    total_entries: int = 0

    seasons_list: list = []
    series_list: list = []

    @classmethod
    def add_section(cls, title: str):
        if title not in cls.info_json["archives"]:
            cls.info_json["archives"][title] = {
                "episodes": []
            }

    @classmethod
    def update_section(cls, title: str, archives: list):
        cls.info_json["archives"][title]["episodes"].extend(archives)

    @classmethod
    def get_total_data(cls):
        return len(cls.seasons_list) + len(cls.series_list)
        
class SpaceListParser(Parser):
    def __init__(self, callback: ParseCallback):
        super().__init__()

        self.callback = callback

    def get_mid(self, url: str):
        mid = self.re_find_str(r"/([0-9]+)/", url)

        return mid[0]

    def get_season_series_id(self, url: str):
        id = self.re_find_str(r"/([0-9]+)\?type", url)

        return id[0]

    def get_sid(self, url: str):
        sid = self.re_find_str(r"sid=([0-9]+)", url)

        return sid[0]

    def get_season_info(self, mid: int, season_id: int, page_num: int = 1):
        params = {
            "mid": mid,
            "season_id": season_id,
            "page_num": page_num,
            "page_size": 30
        }

        url = f"https://api.bilibili.com/x/polymer/web-space/seasons_archives_list?{WbiUtils.encWbi(params)}"

        resp = self.request_get(url, headers = RequestUtils.get_headers(referer_url = self.bilibili_url, sessdata = Config.User.SESSDATA))

        section_title = resp["data"]["meta"]["name"]
        episodes = resp["data"]["archives"]

        Section.add_section(section_title)
        Section.update_section(section_title, episodes)

        Section.total_entries += len(episodes)

        return section_title, resp["data"]["meta"]["total"]

    def get_series_meta_info(self, series_id: int):
        params = {
            "series_id": series_id,
        }

        url = f"https://api.bilibili.com/x/series/series?{self.url_encode(params)}"

        resp = self.request_get(url, headers = RequestUtils.get_headers(referer_url = self.bilibili_url, sessdata = Config.User.SESSDATA))

        section_title = resp["data"]["meta"]["name"]

        Section.add_section(section_title)

        return section_title, resp["data"]["meta"]["total"]

    def get_series_archives_info(self, mid: int, series_id: int, section_title: str, pn: int = 1):
        params = {
            "mid": mid,
            "series_id": series_id,
            "pn": pn,
            "ps": 30
        }

        url = f"https://api.bilibili.com/x/series/archives?{self.url_encode(params)}"

        resp = self.request_get(url, headers = RequestUtils.get_headers(referer_url = "https://www.bilibili.com"))

        archives = resp["data"]["archives"]

        Section.update_section(section_title, archives)

        Section.total_entries += len(archives)
    
    def get_season_series_info(self, mid: int, page_num: int = 1):
        params = {
            "mid": mid,
            "page_num": page_num,
            "page_size": 20,
        }

        url = f"https://api.bilibili.com/x/polymer/web-space/seasons_series_list?{WbiUtils.encWbi(params)}"

        resp = self.request_get(url, headers = RequestUtils.get_headers(referer_url = self.bilibili_url, sessdata = Config.User.SESSDATA))

        items_list = resp["data"]["items_lists"]

        Section.seasons_list.extend([entry["meta"]["season_id"] for entry in items_list.get("seasons_list")])
        Section.series_list.extend([entry["meta"]["series_id"] for entry in items_list.get("series_list")])

        return items_list["page"]["total"]
    
    def get_video_available_media_info(self):
        from utils.parse.video import VideoParser
        
        episode: dict = list(Section.info_json["archives"].values())[0]["episodes"][0]

        VideoParser.get_video_available_media_info(episode.get("bvid"), VideoParser.get_video_cid(episode.get("bvid")))

    def parse_worker(self, url: str):
        self.clear_space_info()

        mid = self.get_mid(url)

        time.sleep(0.5)

        self.callback.onChangeProcessingType(ProcessingType.Page)

        if "list" in url:
            if "space" in url:
                if "type" in url:
                    season_series_id = self.get_season_series_id(url)

                    if "season" in url:
                        self.parse_season_info(mid, season_series_id)
                    else:
                        self.parse_series_info(mid, season_series_id)
                else:
                    self.parse_season_series_info(mid)
            else:
                series_id = self.get_sid(url)

                self.parse_series_info(mid, series_id)
        
        self.parse_episodes()

        self.get_video_available_media_info()

        return StatusCode.Success.value

    def parse_season_info(self, mid: str, season_id: int):
        section_title, total = self.get_season_info(mid, season_id)
        total_page = self.get_total_page(total)

        self.onUpdateName(section_title)
        self.onUpdateTitle(1, total_page, Section.total_entries)

        for i in range(1, total_page):
            page = i + 1

            self.get_season_info(mid, season_id, page)

            self.onUpdateTitle(page, total_page, Section.total_entries)

    def parse_series_info(self, mid: int, series_id: int):
        section_title, total = self.get_series_meta_info(series_id)
        total_page = self.get_total_page(total)

        self.onUpdateName(section_title)
        self.onUpdateTitle(1, total_page, Section.total_entries)

        for i in range(total_page):
            page = i + 1

            self.get_series_archives_info(mid, series_id, section_title, page)

            self.onUpdateTitle(page, total_page, Section.total_entries)

    def parse_season_series_info(self, mid: int):
        total = self.get_season_series_info(mid)
        total_page = self.get_total_page(total)

        self.onUpdateName("合集列表")
        self.onUpdateTitle(1, total_page, Section.get_total_data())

        for i in range(1, total_page):
            page = i + 1

            self.get_season_series_info(mid, page)

            self.onUpdateTitle(page, total_page, Section.get_total_data())

        for season_id in Section.seasons_list:
            self.parse_season_info(mid, season_id)

            time.sleep(1)

        for series_id in Section.series_list:
            self.parse_series_info(mid, series_id)

            time.sleep(1)

    def parse_episodes(self):
        Episode.List.parse_episodes(Section.info_json)

    def clear_space_info(self):
        Section.info_json = {
            "archives": {}
        }

        Section.total_entries = 0

        Section.seasons_list.clear()
        Section.series_list.clear()

    def onUpdateName(self, name: str):
        self.callback.onUpdateName(name)

    def onUpdateTitle(self, page: int, total_page: int, total_data: int):
        self.callback.onUpdateTitle(f"当前第 {page} 页，共 {total_page} 页，已解析 {total_data} 条数据")

        time.sleep(0.3)

    def get_total_page(self, total: int):
        return math.ceil(total / 30)
    
    def get_parse_type_str(self):
        return "合集列表"