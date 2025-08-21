from utils.config import Config

from utils.auth.wbi import WbiUtils

from utils.common.request import RequestUtils
from utils.common.model.callback import ParseCallback
from utils.common.enums import StatusCode
from utils.common.map import rid_map
from utils.common.regex import Regex
from utils.common.exception import GlobalException

from utils.parse.parser import Parser
from utils.parse.episode.episode_v2 import Episode

class PopularParser(Parser):
    def __init__(self, callback: ParseCallback):
        super().__init__()

        self.callback = callback

    def get_weekly_number(self, url: str):
        number = self.re_find_str(r"num=([0-9]+)", url)

        return number[0]

    def get_rid(self, url: str):
        for key, value in rid_map.items():
            if key in url:
                return value.get("rid"), value.get("desc")
            
        raise GlobalException(message = "暂不支持解析此类链接", callback = self.callback.onError)

    def get_popular_weekly_list(self, number: int):
        params = {
            "number": number
        }

        url = f"https://api.bilibili.com/x/web-interface/popular/series/one?number={number}&{WbiUtils.encWbi(params)}"

        resp = self.request_get(url, headers = RequestUtils.get_headers(referer_url = self.bilibili_url, sessdata = Config.User.SESSDATA))

        self.info_json: dict = resp["data"].copy()

    def get_popular_rank_list(self, rid: int, desc: str):
        params = {
            "rid": rid,
            "type": "all"
        }

        url = f"https://api.bilibili.com/x/web-interface/ranking/v2?{WbiUtils.encWbi(params)}"

        resp = self.request_get(url, headers = RequestUtils.get_headers(referer_url = self.bilibili_url, sessdata = Config.User.SESSDATA))

        self.info_json: dict = resp["data"].copy()

        self.info_json["config"] = {
            "label": f"{desc}排行榜"
        }

    def get_popular_available_media_info(self):
        from utils.parse.video import VideoParser

        episode: dict = self.info_json["list"][0]

        bvid, self.cid = episode.get("bvid"), episode.get("cid")

        self.parse_episodes()

        VideoParser.get_video_available_media_info(bvid, self.cid)

    def parse_worker(self, url: str):
        match Regex.find_string(r"weekly|rank", url):
            case "weekly":
                number = self.get_weekly_number(url)

                self.get_popular_weekly_list(number)

            case "rank":
                rid, desc = self.get_rid(url)

                self.get_popular_rank_list(rid, desc)

        self.get_popular_available_media_info()

        return StatusCode.Success.value

    def parse_episodes(self):
        Episode.Popular.parse_episodes(self.info_json, self.cid)

    def get_parse_type_str(self):
        return "热榜"
        