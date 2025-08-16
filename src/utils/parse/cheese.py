from utils.config import Config

from utils.common.enums import StatusCode
from utils.common.model.callback import ParseCallback
from utils.common.request import RequestUtils
from utils.common.regex import Regex

from utils.parse.episode_v2 import Episode
from utils.parse.audio import AudioInfo
from utils.parse.parser import Parser
from utils.parse.preview import PreviewInfo

class CheeseInfo:
    aid: int = 0
    ep_id: int = 0
    cid: int = 0
    season_id: int = 0

    info_json: dict = {}

    @classmethod
    def clear_cheese_info(cls):
        cls.aid = 0
        cls.ep_id = 0
        cls.cid = 0
        cls.season_id = 0
            
        cls.info_json.clear()

class CheeseParser(Parser):
    def __init__(self, callback: ParseCallback):
        super().__init__()

        self.callback = callback

    def get_epid(self, url: str):
        epid = self.re_find_str(r"ep([0-9]+)", url)

        self.url_type, self.url_type_value = "ep_id", epid[0]

    def get_season_id(self, url: str):
        season_id = self.re_find_str(r"ss([0-9]+)", url)

        self.url_type, self.url_type_value, CheeseInfo.season_id = "season_id", season_id[0], season_id[0]

    def get_cheese_info(self):
        url = f"https://api.bilibili.com/pugv/view/web/season/v2?{self.url_type}={self.url_type_value}"

        resp = self.request_get(url, headers = RequestUtils.get_headers(sessdata = Config.User.SESSDATA))

        info_data = resp["data"]

        if len(info_data["sections"]) > 1:
            info_data["sections"] = [section for section in info_data["sections"] if section["title"] != "默认章节"]

        CheeseInfo.ep_id = info_data["sections"][0]["episodes"][0]["id"]

        CheeseInfo.info_json = info_data.copy()

        self.parse_episodes()

    def get_cheese_available_media_info(self):
        params = {
            "avid": CheeseInfo.aid,
            "ep_id": CheeseInfo.ep_id,
            "cid": CheeseInfo.cid,
            "fnver": 0,
            "fnval": 4048,
            "fourk": 1
        }

        url = f"https://api.bilibili.com/pugv/player/web/playurl?{self.url_encode(params)}"

        resp = self.request_get(url, headers = RequestUtils.get_headers(referer_url = self.bilibili_url, sessdata = Config.User.SESSDATA))

        PreviewInfo.download_json = resp["data"].copy()

    def parse_worker(self, url: str):
        self.clear_cheese_info()

        match Regex.find_string(r"ep|ss", url):
            case "ep":
                self.get_epid(url)

            case "ss":
                self.get_season_id(url)

        self.get_cheese_info()

        self.get_cheese_available_media_info()

        return StatusCode.Success.value

    def parse_episodes(self):
        if self.url_type == "season_id":
            ep_id = CheeseInfo.ep_id
        else:
            ep_id = int(self.url_type_value)

        Episode.Cheese.parse_episodes(CheeseInfo.info_json, ep_id)

    def clear_cheese_info(self):
        CheeseInfo.clear_cheese_info()

        AudioInfo.clear_audio_info()

    def get_parse_type_str(self):
        return "课程"
