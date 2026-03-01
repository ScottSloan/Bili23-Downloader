from util.parse.episode.cheese import CheeseEpisodeParser
from util.network.request import NetworkRequestWorker
from util.parse.parser.base import ParserBase
from util.thread import SyncTask

class CheeseParser(ParserBase):
    def __init__(self):
        super().__init__()
        
    def get_ep_id(self):
        ep_id = self.find_str(r"ep([0-9]+)", self.url)

        return f"ep_id={ep_id}"
    
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

        episode_parser = CheeseEpisodeParser(self.info_data)
        episode_parser.parse()

    def get_cheese_info(self, param: str):
        def on_success(response: dict):
            self.info_data = response

        url = f"https://api.bilibili.com/pugv/view/web/season/v2?{param}"

        worker = NetworkRequestWorker(url)
        worker.success.connect(on_success)
        worker.error.connect(self.on_error)

        SyncTask.run(worker)

        self.check_response(self.info_data)

    def get_category_name(self):
        # 课程
        return "COURSE"
    