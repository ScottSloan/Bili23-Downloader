import re
import json
import requests

from utils.common.enums import StatusCode
from utils.tool_v2 import RequestTool, UniversalTool
from utils.common.exception import GlobalException
from utils.common.data_type import ParseCallback

class CheeseInfo:
    url: str = ""
    epid: int = 0
    season_id: int = 0

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

        with open("cheese.json", "w", encoding = "utf-8") as f:
            f.write(req.text)

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
