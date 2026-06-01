from ...common.enum import ParserType
from ...network.request import SyncNetWorkRequest
from ..episode.cheese import CheeseEpisodeParser
from .base import ParserBase

class CheeseParser(ParserBase):
    def __init__(self):
        super().__init__()

        self.ep_id = None
        
    def get_ep_id(self):
        self.ep_id = self.find_str(r"ep([0-9]+)", self.url)

        return f"ep_id={self.ep_id}"
    
    def get_season_id(self):
        season_id = self.find_str(r"ss([0-9]+)", self.url)

        return f"season_id={season_id}"
    
    def parse(self, url: str, pn: int):
        self.url = url

        match self.find_str(r"ep|ss", url):
            case "ep":
                param = self.get_ep_id()

            case "ss":
                param = self.get_season_id()

        self.get_cheese_info(param)

        episode_parser = CheeseEpisodeParser(self.info_data, self.get_category_name())
        episode_parser.parse()

    def get_cheese_info(self, param: str):
        url = f"https://api.bilibili.com/pugv/view/web/season/v2?{param}"

        request = SyncNetWorkRequest(url, raise_for_status = self.raise_for_status)
        response = request.run()

        self.check_response(response)

        self.info_data = response

        if self.ep_id:
            self.info_data["data"]["current_ep_id"] = int(self.ep_id)

    def get_parser_type(self):
        return ParserType.CHEESE
    