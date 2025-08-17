from utils.config import Config

from utils.common.enums import StatusCode
from utils.common.model.callback import ParseCallback
from utils.common.request import RequestUtils
from utils.common.regex import Regex

from utils.parse.episode_v2 import Episode
from utils.parse.audio import AudioInfo
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

        self.info_json: dict = resp["data"].copy()

        if len(self.info_json["sections"]) > 1:
            self.info_json["sections"] = [section for section in self.info_json["sections"] if section["title"] != "默认章节"]

        episode: dict = self.info_json["sections"][0]["episodes"][0]

        if param.startswith("season_id"):
            self.ep_id = episode.get("id")

        self.parse_episodes()

    def get_cheese_available_media_info(self, aid: int, ep_id: int, cid: int):
        params = {
            "avid": aid,
            "ep_id": ep_id,
            "cid": cid,
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
                param = self.get_epid(url)

            case "ss":
                param = self.get_season_id(url)

        self.get_cheese_info(param)

        episode: dict = Episode.Utils.get_current_episode()

        self.get_cheese_available_media_info(episode.get("aid"), episode.get("ep_id"), episode.get("cid"))

        return StatusCode.Success.value

    def parse_episodes(self):
        Episode.Cheese.parse_episodes(self.info_json, self.ep_id)

    def clear_cheese_info(self):
        AudioInfo.clear_audio_info()

    def get_parse_type_str(self):
        return "课程"
