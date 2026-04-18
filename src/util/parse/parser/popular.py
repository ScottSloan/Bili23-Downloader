from util.network import SyncNetWorkRequest

from ..episode.popular import PopularEpisodeParser
from .base import ParserBase

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
        params = {
            "number": self.weekly_number,
            "web_location": "333.934"
        }

        url = f"https://api.bilibili.com/x/web-interface/popular/series/one?{self.enc_wbi(params)}"

        request = SyncNetWorkRequest(url)
        response = request.run()

        self.check_response(response)

        self.info_data = response

    def get_category_name(self):
        # 每周必看
        return "WEEKLY"
    