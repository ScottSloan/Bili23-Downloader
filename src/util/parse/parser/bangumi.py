from util.parse.episode.bangumi import BangumiEpisodeParser
from util.network.request import NetworkRequestWorker
from util.common.data import bangumi_type_map
from util.parse.parser.base import ParserBase
from util.thread import SyncTask

class BangumiParser(ParserBase):
    def __init__(self):
        super().__init__()

        self.ep_id = None

    def get_ep_id(self):
        self.ep_id = self.find_str(r"ep([0-9]+)", self.url)

        return f"ep_id={self.ep_id}"
    
    def get_season_id(self):
        season_id = self.find_str(r"ss([0-9]+)", self.url)

        return f"season_id={season_id}"

    def get_media_id(self):
        def on_success(response: dict):
            self.check_response(response)

            nonlocal season_id

            season_id = response["result"]["media"]["season_id"]
        
        media_id = self.find_str(r"md([0-9]+)", self.url)
        season_id = 0

        url = f"https://api.bilibili.com/pgc/review/user?media_id={media_id}"

        worker = NetworkRequestWorker(url)
        worker.success.connect(on_success)
        worker.error.connect(self.on_error)

        SyncTask.run(worker)

        return f"season_id={season_id}"

    def parse(self, url: str, pn: int):
        self.url = url

        match self.find_str(r"ep|ss|md", url):
            case "ep":
                param = self.get_ep_id()

            case "ss":
                param = self.get_season_id()

            case "md":
                param = self.get_media_id()

        self.get_bangumi_info(param)

        episode_parser = BangumiEpisodeParser(self.info_data.copy(), self.get_category_name())
        episode_parser.parse()

    def get_bangumi_info(self, param: str):
        def on_success(response: dict):
            self.info_data = response

            if self.ep_id:
                self.info_data["result"]["current_ep_id"] = int(self.ep_id)
        
        url = f"https://api.bilibili.com/pgc/view/web/season?{param}"

        worker = NetworkRequestWorker(url)
        worker.success.connect(on_success)
        worker.error.connect(self.on_error)

        SyncTask.run(worker)

        self.check_response(self.info_data)

    def get_category_name(self):
        return bangumi_type_map.get(self.info_data["result"]["type"])
