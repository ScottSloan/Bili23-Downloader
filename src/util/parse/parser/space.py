from ...common.enum import ParserType
from ...network.request import SyncNetWorkRequest
from ..episode.space import SpaceEpisodeParser
from .base import ParserBase


from urllib.parse import urlparse
import math

class Data:
    uname_map: dict[int, str] = {}

class SpaceParser(ParserBase):
    def __init__(self):
        super().__init__()

        self.ps = 40

    def get_mid(self):
        # 只在路径部分匹配，避免链接中的查询参数（如搜索关键词）干扰 uid 的提取
        mid = self.find_str(r"/([0-9]+)", urlparse(self.url).path)

        return mid

    def parse(self, url: str, pn: int, get_info_data: bool = False):
        self.url = url
        self.pn = pn

        self.mid = self.get_mid()
        self.keyword = self.get_url_keyword()

        self.get_search_arc_info()
        self.get_uname()

        self.set_search_keyword(self.keyword)

        if get_info_data:
            return self.info_data

        episode_parser = SpaceEpisodeParser(self.info_data.copy(), self.get_category_name())
        episode_parser.parse()

    def get_search_arc_info(self):
        params = {
            "pn": self.pn,
            "ps": self.ps,
            "tid": 0,
            "special_type": "",
            "order": "pubdate",
            "mid": self.mid,
            "index": 0,
            "keyword": self.keyword,
            "order_avoided": "true",
            "platform": "web",
            "web_location": "333.1387",
            "dm_img_list": "[]",
            "dm_img_str": "V2ViR0wgMS4wIChPcGVuR0wgRVMgMi4wIENocm9taXVtKQ",
            "dm_cover_img_str": "QU5HTEUgKE5WSURJQSwgTlZJRElBIEdlRm9yY2UgUlRYIDQwNjAgTGFwdG9wIEdQVSAoMHgwMDAwMjhFMCkgRGlyZWN0M0QxMSB2c181XzAgcHNfNV8wLCBEM0QxMSlHb29nbGUgSW5jLiAoTlZJRElBKQ",
            "dm_img_inter": '{"ds":[],"wh":[3688,4546,12],"of":[119,238,119]}',
        }

        url = f"https://api.bilibili.com/x/space/wbi/arc/search?{self.enc_wbi(params)}"

        request = SyncNetWorkRequest(url, raise_for_status = self.raise_for_status)
        response = request.run()

        self.check_response(response)

        self.info_data = response

    def get_uname(self):
        if self.mid in Data.uname_map:
            self.update_space_owner_info()

        url = f"https://api.bilibili.com/x/web-interface/card?mid={self.mid}"

        request = SyncNetWorkRequest(url, raise_for_status = self.raise_for_status)
        response = request.run()

        self.check_response(response)

        Data.uname_map[self.mid] = response["data"]["card"]["name"]

        self.update_space_owner_info()

    def update_space_owner_info(self):
        self.info_data["data"]["info"] = {
            "name": Data.uname_map.get(self.mid, ""),
            "mid": self.mid
        }
    
    def get_parser_type(self):
        return ParserType.SPACE
    
    def get_extra_data(self):
        count = self.info_data["data"]["page"]["count"]
        
        return {
            "pagination": True,
            "pagination_data": {
                "total_pages": math.ceil(count / self.ps),
                "total_items": count,
                "current_page": self.pn
            },
            "server_search": True,
            "keyword": self.keyword
        }
    