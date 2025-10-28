from utils.config import Config

from utils.common.enums import StatusCode
from utils.common.model.callback import ParseCallback
from utils.common.request import RequestUtils
from utils.common.regex import Regex
from utils.common.datetime_util import DateTime

from utils.parse.episode.episode_v2 import Episode
from utils.parse.episode.cheese import Cheese
from utils.parse.parser import Parser
from utils.parse.preview import PreviewInfo

class CheeseParser(Parser):
    def __init__(self, callback: ParseCallback):
        super().__init__()

        self.callback = callback

    def get_epid(self, url: str):
        epid = self.re_find_str(r"ep([0-9]+)", url)

        self.ep_id = int(epid[0])

        return f"ep_id={epid[0]}"

    def get_season_id(self, url: str):
        season_id = self.re_find_str(r"ss([0-9]+)", url)

        return f"season_id={season_id[0]}"

    def get_cheese_info(self, param: str):
        url = f"https://api.bilibili.com/pugv/view/web/season/v2?{param}"

        resp = self.request_get(url, headers = RequestUtils.get_headers(sessdata = Config.User.SESSDATA))

        self.info_json: dict = self.json_get(resp, "data")

        if param.startswith("season_id"):
            self.ep_id = self.get_sections_epid()

        self.parse_episodes()

    @classmethod
    def get_cheese_available_media_info(cls, aid: int, ep_id: int, cid: int):
        params = {
            "avid": aid,
            "cid": cid,
            "qn": 0,
            "fnver": 0,
            "fnval": 16,
            "fourk": 1,
            "ep_id": ep_id,
        }

        url = f"https://api.bilibili.com/pugv/player/web/playurl?{cls.url_encode(params)}"

        resp = cls.request_get(url, headers = RequestUtils.get_headers(referer_url = cls.bilibili_url, sessdata = Config.User.SESSDATA))

        data = cls.json_get(resp, "data")

        cls.check_drm_protection(data)

        PreviewInfo.download_json = data

    @classmethod
    def get_cheese_season_info(cls, season_id: int):
        params = {
            "season_id": season_id
        }

        url = f"https://api.bilibili.com/pugv/view/web/season/v2?{cls.url_encode(params)}"

        resp = cls.request_get(url, headers = RequestUtils.get_headers(referer_url = cls.bilibili_url, sessdata = Config.User.SESSDATA))

        info_json: dict = cls.json_get(resp, "data")

        return {
            "description": info_json.get("subtitle"),
            "poster_url": info_json.get("cover"),
            "pubdate": DateTime.time_str_from_timestamp(info_json["sections"][0]["episodes"][0]["release_date"], "%Y-%m-%d")
        }

    def parse_worker(self, url: str):
        match Regex.find_string(r"ep|ss", url):
            case "ep":
                param = self.get_epid(url)

            case "ss":
                param = self.get_season_id(url)

        self.get_cheese_info(param)

        episode: dict = Episode.Utils.get_first_episode()

        if episode:
            self.get_cheese_available_media_info(episode.get("aid"), episode.get("ep_id"), episode.get("cid"))

        self.callback.onUpdateHistory(url, self.info_json.get("title"), self.get_parse_type_str())

        return StatusCode.Success.value

    def parse_episodes(self):
        Cheese.parse_episodes(self.info_json, self.ep_id)

    def get_parse_type_str(self):
        return "课程"

    def get_sections_epid(self):
        for section in self.info_json["sections"]:
            for episode in section["episodes"]:
                return episode.get("id")
