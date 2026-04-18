from util.network import SyncNetWorkRequest

from ..episode.list import ListEpisodeParser
from .base import ParserBase

from urllib.parse import urlencode
import math

class ListParser(ParserBase):
    def __init__(self):
        super().__init__()

    def get_mid(self):
        mid = self.find_str(r"/([0-9]+)", self.url)

        return mid
    
    def get_season_id(self):
        season_id = self.find_str(r"/([0-9]+)\?type=season", self.url)

        return season_id
    
    def get_series_id(self):
        series_id = self.find_str(r"/([0-9]+)\?type=series", self.url)

        return series_id

    def get_sid(self):
        sid = self.find_str(r"sid=([0-9]+)", self.url)

        return sid

    def parse(self, url: str, pn: int):
        self.url = url
        self.pn = pn

        self.mid = self.get_mid()

        if "type=" in self.url:
            # 根据 url 中的 type 参数判断是合集还是系列
            match self.find_str(r"type=(season|series)", self.url):
                case "season":
                    self.season_id = self.get_season_id()

                    self.get_seasons_archives_list()

                case "series":
                    self.series_id = self.get_series_id()

                    self.get_series_archives_list()
                    self.get_series_meta_info()

        elif "sid=" in self.url:
            self.series_id = self.get_sid()

            self.get_series_archives_list()
            self.get_series_meta_info()

        else:
            raise ValueError("无效的链接")

        episode_parser = ListEpisodeParser(self.info_data.copy(), self.get_category_name())
        episode_parser.parse()

    def get_seasons_archives_list(self):
        # 合集，以 season_id 区分
        # 形如 https://space.bilibili.com/{mid}/lists/{season_id}?type=season
        params = {
            "mid": self.mid,
            "season_id": self.season_id,
            "sort_reverse": "false",
            "page_size": 30,
            "page_num": self.pn,
            "web_location": "333.1387",
        }

        url = f"https://api.bilibili.com/x/polymer/web-space/seasons_archives_list?{urlencode(params)}"

        request = SyncNetWorkRequest(url)
        response = request.run()

        self.check_response(response)

        self.info_data = response

    def get_series_archives_list(self):
        # 系列，以 series_id 区分
        # 形如 https://space.bilibili.com/{mid}/lists/{series_id}?type=series
        params = {
            "mid": self.mid,
            "series_id": self.series_id,
            "only_normal": "true",
            "sort": "desc",
            "ps": 30,
            "pn": self.pn,
            "web_location": "333.1387",
        }

        url = f"https://api.bilibili.com/x/series/archives?{urlencode(params)}"

        request = SyncNetWorkRequest(url)
        response = request.run()

        self.check_response(response)

        self.info_data = response

    def get_series_meta_info(self):
        # 由于系列的接口不含 meta 信息，还需要额外获取
        params = {
            "series_id": self.series_id,
            "web_location": "333.1387"
        }

        url = f"https://api.bilibili.com/x/series/series?{urlencode(params)}"

        request = SyncNetWorkRequest(url)
        response = request.run()

        self.check_response(response)

        self.info_data["data"]["meta"] = response["data"]["meta"].copy()

    def get_category_name(self):
        # 合集列表
        return "COLLECTION_LIST"
    
    def get_extra_data(self):
        count = self.info_data["data"]["page"]["total"]

        return {
            "pagination": True,
            "pagination_data": {
                "total_pages": math.ceil(count / 30),
                "total_items": count,
                "current_page": self.pn
            }
        }
    