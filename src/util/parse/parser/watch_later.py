from util.parse.episode.watch_later import WatchLaterEpisodeParser
from util.network.request import NetworkRequestWorker
from util.parse.parser.base import ParserBase
from util.thread import SyncTask

import math

class WatchLaterParser(ParserBase):
    def __init__(self):
        super().__init__()

    def parse(self, url: str, pn: int):
        self.url = url
        self.pn = pn

        self.get_history_info()

        episode_parser = WatchLaterEpisodeParser(self.info_data.copy())
        episode_parser.parse()

    def get_history_info(self):
        def on_success(response: dict):
            self.info_data = response

        params = {
            "pn": self.pn,
            "ps": 20,
            "viewed": 0,
            "key": "",
            "asc": False,
            "need_split": True,
            "web_location": "333.881"
        }

        url = f"https://api.bilibili.com/x/v2/history/toview/web?{self.enc_wbi(params)}"
        
        worker = NetworkRequestWorker(url)
        worker.success.connect(on_success)
        worker.error.connect(self.on_error)
        
        SyncTask.run(worker)

        self.check_response(self.info_data)

    def get_category_name(self):
        return "WATCH_LATER"
    
    def get_extra_data(self):
        count = self.info_data["data"]["count"]

        return {
            "pagination": True,
            "pagination_data": {
                "total_pages": math.ceil(count / 40),
                "total_items": count,
            }
        }
