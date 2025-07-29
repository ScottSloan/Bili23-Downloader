from utils.config import Config

from utils.auth.wbi import WbiUtils

from utils.common.request import RequestUtils
from utils.common.data_type import ParseCallback
from utils.common.enums import StatusCode
from utils.common.map import rid_map
from utils.common.regex import Regex

from utils.parse.parser import Parser
from utils.parse.episode_v2 import Episode
from utils.parse.video import VideoParser, VideoInfo

class PopularInfo:
    number: int = 0
    rid: int = 0
    rid_desc: str = ""

    info_json: dict = {}

class PopularParser(Parser):
    def __init__(self, callback: ParseCallback):
        super().__init__()

        self.callback = callback

    def get_one_number(self, url: str):
        number = self.re_find_str(r"num=([0-9]+)", url)

        PopularInfo.number = number[0]

    def get_rid(self, url: str):
        for key, value in rid_map.items():
            if key in url:
                PopularInfo.rid = value.get("rid")
                PopularInfo.rid_desc = value.get("desc")
                return

    def get_popular_one_list(self):
        params = {
            "number": PopularInfo.number
        }

        url = f"https://api.bilibili.com/x/web-interface/popular/series/one?number={PopularInfo.number}&{WbiUtils.encWbi(params)}"

        resp = self.request_get(url, headers = RequestUtils.get_headers(referer_url = self.bilibili_url, sessdata = Config.User.SESSDATA))

        PopularInfo.info_json = resp["data"].copy()

    def get_popular_rank_list(self):
        params = {
            "rid": PopularInfo.rid,
            "type": "all"
        }

        url = f"https://api.bilibili.com/x/web-interface/ranking/v2?rid={PopularInfo.rid}&type=all&{WbiUtils.encWbi(params)}"

        resp = self.request_get(url, headers = RequestUtils.get_headers(referer_url = self.bilibili_url, sessdata = Config.User.SESSDATA))

        PopularInfo.info_json = resp["data"].copy()

        PopularInfo.info_json["config"] = {
            "label": f"{PopularInfo.rid_desc}排行榜"
        }

    def get_popular_available_media_info(self):
        episode = PopularInfo.info_json["list"][0]

        VideoInfo.bvid = episode["bvid"]
        VideoInfo.cid = episode["cid"]

        VideoParser.get_video_available_media_info()

    def parse_worker(self, url: str):
        match Regex.find_string(r"one|rank", url):
            case "one":
                self.get_one_number(url)

                self.get_popular_one_list()

            case "rank":
                self.get_rid(url)

                self.get_popular_rank_list()

        self.get_popular_available_media_info()

        return StatusCode.Success.value

    def parse_episodes(self):
        Episode.Popular.parse_episodes(PopularInfo.info_json)
        