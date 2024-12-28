import re
import json
import requests

from utils.common.enums import StatusCode
from utils.tool_v2 import RequestTool, UniversalTool
from utils.common.exception import GlobalException
from utils.common.data_type import ParseCallback
from utils.parse.episode import EpisodeInfo, cheese_episode_parser

class CheeseInfo:
    url: str = ""
    epid: int = 0
    season_id: int = 0

    title: str = ""
    subtitle: str = ""

    episodes_list: list = []

    info_json: dict = {}

class CheeseParser:
    def __init__(self, callback: ParseCallback):
        self.callback = callback

    def get_epid(self, url: str):
        epid = re.findall(r"ep([0-9]+)", url)

        if not epid:
            raise Exception(StatusCode.URL.value)

        self.url_type, self.url_type_value = "ep_id", epid[0]

    def get_season_id(self, url: str):
        season_id = re.findall(r"ss([0-9]+)", url)

        if not season_id:
            raise Exception(StatusCode.URL.value)

        self.url_type, self.url_type_value, CheeseInfo.season_id = "season_id", season_id[0], season_id[0]

    def get_cheese_info(self):
        url = f"https://api.bilibili.com/pugv/view/web/season?{self.url_type}={self.url_type_value}"

        req = requests.get(url, headers = RequestTool.get_headers(), proxies = RequestTool.get_proxies(), auth = RequestTool.get_auth(), timeout = 5)
        resp = json.loads(req.text)

        self.check_json(resp)

        info_data = CheeseInfo.info_json = resp["data"]

        CheeseInfo.url = info_data["share_url"]
        CheeseInfo.title = info_data["title"]
        CheeseInfo.subtitle = info_data["subtitle"]

        CheeseInfo.episodes_list = info_data["episodes"]
        CheeseInfo.epid = CheeseInfo.episodes_list[0]["id"]

        self.parse_episodes()

    def parse_url(self, url: str):
        def worker():
            match UniversalTool.re_find_string(r"ep|ss", url):
                case "ep":
                    self.get_epid(url)

                case "ss":
                    self.get_season_id(url)

            self.get_cheese_info()

            return StatusCode.Success.value

        try:
            return worker()

        except Exception as e:
            raise GlobalException(e, callback = self.callback.error_callback)
    
    def check_json(self, json: dict):
        # 检查接口返回状态码
        status_code = json["code"]

        if status_code != StatusCode.Success.value:
            raise Exception(status_code)

    def parse_episodes(self):
        EpisodeInfo.clear_episode_data()

        if self.url_type == "season_id":
            ep_id = CheeseInfo.epid
        else:
            ep_id = int(self.url_type_value)

        cheese_episode_parser(CheeseInfo.info_json, ep_id)
    