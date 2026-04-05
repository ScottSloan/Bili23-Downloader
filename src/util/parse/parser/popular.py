from util.parse.episode.popular import PopularEpisodeParser
from util.network.request import NetworkRequestWorker
from util.parse.parser.base import ParserBase
from util.thread import SyncTask

class PopularParser(ParserBase):
    def __init__(self):
        super().__init__()

    def get_weekly_number(self):
        number = self.find_str(r"num=([0-9]+)", self.url)

        return number

    def parse(self, url: str, pn: int):
        self.url = url
        
        self.weekly_number = self.get_weekly_number()

        self.get_popular_weekly_list()

        episode_parser = PopularEpisodeParser(self.info_data.copy(), self.get_category_name())
        episode_parser.parse()

    def get_popular_weekly_list(self):
        def on_success(response: dict):
            self.info_data = response

        params = {
            "number": self.weekly_number,
            "web_location": "333.934"
        }

        url = f"https://api.bilibili.com/x/web-interface/popular/series/one?{self.enc_wbi(params)}"

        worker = NetworkRequestWorker(url)
        worker.success.connect(on_success)
        worker.error.connect(self.on_error)

        SyncTask.run(worker)

        self.check_response(self.info_data)

    def get_category_name(self):
        # 每周必看
        return "WEEKLY"
    