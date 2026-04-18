from util.network import SyncNetWorkRequest

from ..episode.space import SpaceEpisodeParser
from .base import ParserBase

import math

class Data:
    uname_map: dict[int, str] = {}

class SpaceParser(ParserBase):
    def __init__(self):
        super().__init__()

        self.ps = 40

    def get_mid(self):
        mid = self.find_str(r"/([0-9]+)", self.url)

        return mid

    def parse(self, url: str, pn: int):
        self.url = url
        self.pn = pn

        self.mid = self.get_mid()

        self.get_search_arc_info()
        self.get_uname()

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
            "keyword": "",
            "order_avoided": "true",
            "platform": "web",
            "web_location": "333.1387",
            "dm_img_list": "[]",
            "dm_img_str": "V2ViR0wgMS4wIChPcGVuR0wgRVMgMi4wIENocm9taXVtKQ",
            "dm_cover_img_str": "QU5HTEUgKE5WSURJQSwgTlZJRElBIEdlRm9yY2UgUlRYIDQwNjAgTGFwdG9wIEdQVSAoMHgwMDAwMjhFMCkgRGlyZWN0M0QxMSB2c181XzAgcHNfNV8wLCBEM0QxMSlHb29nbGUgSW5jLiAoTlZJRElBKQ",
            "dm_img_inter": '{"ds":[],"wh":[3688,4546,12],"of":[119,238,119]}',
        }

        url = f"https://api.bilibili.com/x/space/wbi/arc/search?{self.enc_wbi(params)}"

        request = SyncNetWorkRequest(url)
        response = request.run()

        self.check_response(response)

        self.info_data = response

    def get_uname(self):
        if self.mid in Data.uname_map:
            self.update_space_owner_info()

        url = f"https://api.bilibili.com/x/web-interface/card?mid={self.mid}"

        request = SyncNetWorkRequest(url)
        response = request.run()

        self.check_response(response)

        Data.uname_map[self.mid] = response["data"]["card"]["name"]

        self.update_space_owner_info()

    def update_space_owner_info(self):
        self.info_data["data"]["info"] = {
            "name": Data.uname_map.get(self.mid, ""),
            "mid": self.mid
        }

    def get_category_name(self):
        # 个人空间
        return "PROFILE"
    
    def get_extra_data(self):
        count = self.info_data["data"]["page"]["count"]
        
        return {
            "pagination": True,
            "pagination_data": {
                "total_pages": math.ceil(count / self.ps),
                "total_items": count,
                "current_page": self.pn
            }
        }
    