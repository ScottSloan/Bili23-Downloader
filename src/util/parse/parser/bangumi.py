from util.common.data import bangumi_type_map
from util.network import SyncNetWorkRequest

from ..episode.bangumi import BangumiEpisodeParser
from .base import ParserBase

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
        media_id = self.find_str(r"md([0-9]+)", self.url)

        url = f"https://api.bilibili.com/pgc/review/user?media_id={media_id}"

        request = SyncNetWorkRequest(url)
        response = request.run()

        self.check_response(response)

        season_id = response["result"]["media"]["season_id"]

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
        url = f"https://api.bilibili.com/pgc/view/web/season?{param}"

        request = SyncNetWorkRequest(url)
        response = request.run()

        self.check_response(response)

        self.info_data = response

        if self.ep_id:
            self.info_data["result"]["current_ep_id"] = int(self.ep_id)

    def get_category_name(self):
        return bangumi_type_map.get(self.info_data["result"]["type"])
    
    def get_extra_data(self):
        return {
            "seasons": True,
            "season_data": {
                "season_list": self._get_season_list(),
                "series_title": self.info_data.get("result", {}).get("series", {}).get("series_title", ""),
                "season_id": self.info_data.get("result", {}).get("season_id", "")
            }
        }
    
    def _get_season_list(self):
        season_list = []

        for entry in self.info_data.get("result", {}).get("seasons", []):
            season_id = entry.get("season_id")

            season_list.append(
                {
                    "title": entry["season_title"],
                    "season_id": season_id,
                    "url": "https://www.bilibili.com/bangumi/play/ss{season_id}".format(season_id = season_id)
                }
            )
            
        return season_list
