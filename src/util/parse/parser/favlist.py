from util.network import SyncNetWorkRequest

from ..episode.favlist import FavlistEpisodeParser
from .base import ParserBase

from urllib.parse import urlencode
import math

class FavlistParser(ParserBase):
    def __init__(self):
        super().__init__()

        self.ps = 40

    def get_media_id(self):
        match self.find_str(r"fid|ml", self.url):
            case "fid":
                return self.find_str(r"fid=(\d+)", self.url)
            
            case "ml":
                return self.find_str(r"ml(\d+)", self.url)

    def parse(self, url: str, pn: int):
        self.url = url
        self.pn = pn

        self.media_id = self.get_media_id()

        self.get_favlist()

        episode_parser = FavlistEpisodeParser(self.info_data, self.get_category_name())
        episode_parser.parse()

    def get_favlist(self):
        params = {
            "media_id": self.media_id,
            "pn": self.pn,
            "ps": self.ps,
            "keyword": "",
            "order": "mtime",
            "type": 0,
            "tid": 0,
            "platform": "web",
            "web_location": "333.1387",
        }

        url = f"https://api.bilibili.com/x/v3/fav/resource/list?{urlencode(params)}"

        request = SyncNetWorkRequest(url)
        response = request.run()

        self.check_response(response)

        self.info_data = response

    def get_category_name(self):
        # 收藏夹
        return "FAVORITES"
    
    def get_extra_data(self):
        count = self.info_data["data"]["info"]["media_count"]

        return {
            "pagination": True,
            "pagination_data": {
                "total_pages": math.ceil(count / self.ps),
                "total_items": count,
                "current_page": self.pn
            }
        }
    