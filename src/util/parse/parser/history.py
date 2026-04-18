from util.network import SyncNetWorkRequest

from ..episode.history import HistoryEpisodeParser
from .base import ParserBase

from urllib.parse import urlencode
import math

class HistoryParser(ParserBase):
    def __init__(self):
        super().__init__()

    def parse(self, url: str, pn: int):
        self.url = url
        self.pn = pn

        self.check_login()

        self.get_history_info()

        episode_parser = HistoryEpisodeParser(self.info_data.copy(), self.get_category_name())
        episode_parser.parse()

    def get_history_info(self):
        params = {
            "pn": self.pn,
            "keyword": "",
            "business": "archive",
            "add_time_start": 0,
            "add_time_end": 0,
            "arc_max_duration": 0,
            "arc_min_duration": 0,
            "device_type": 0,
            "web_location": "333.1391"
        }

        url = f"https://api.bilibili.com/x/web-interface/history/search?{urlencode(params)}"

        request = SyncNetWorkRequest(url)
        response = request.run()

        self.check_response(response)

        self.info_data = response

    def get_category_name(self):
        return "HISTORY"
    
    def get_extra_data(self):
        count = self.info_data["data"]["page"]["total"]

        return {
            "pagination": True,
            "pagination_data": {
                "total_pages": math.ceil(count / 20),
                "total_items": count,
                "current_page": self.pn
            }
        }
