from util.parse.episode.history import HistoryEpisodeParser
from util.network.request import NetworkRequestWorker
from util.parse.parser.base import ParserBase
from util.thread import SyncTask

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

        episode_parser = HistoryEpisodeParser(self.info_data.copy())
        episode_parser.parse()

    def get_history_info(self):
        def on_success(response: dict):
            self.info_data = response

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
        
        worker = NetworkRequestWorker(url)
        worker.success.connect(on_success)
        worker.error.connect(self.on_error)
        
        SyncTask.run(worker)

        self.check_response(self.info_data)

    def get_category_name(self):
        return "HISTORY"
    
    def get_extra_data(self):
        count = self.info_data["data"]["page"]["total"]

        return {
            "pagination": True,
            "pagination_data": {
                "total_pages": math.ceil(count / 20),
                "total_items": count,
            }
        }
