from utils.tool_v2 import UniversalTool
from utils.config import Config

from utils.common.enums import StatusCode, StreamType
from utils.common.exception import GlobalException
from utils.common.data_type import ParseCallback
from utils.common.request import RequestUtils
from utils.common.regex import Regex

from utils.parse.episode_v2 import Episode
from utils.parse.audio import AudioInfo
from utils.parse.parser import Parser

class CheeseInfo:
    url: str = ""
    aid: int = 0
    ep_id: int = 0
    cid: int = 0
    season_id: int = 0

    title: str = ""
    subtitle: str = ""
    views: str = ""
    release: str = ""
    expiry: str = ""

    stream_type: str = ""

    up_name: str = ""
    up_mid: int = 0

    info_json: dict = {}
    download_json: dict = {}

    @classmethod
    def clear_cheese_info(cls):
        cls.url = ""
        cls.title = ""
        cls.subtitle = ""
        cls.views = 0
        cls.release = ""
        cls.expiry = ""
        cls.aid = 0
        cls.ep_id = 0
        cls.cid = 0
        cls.season_id = 0
        cls.up_name = ""
        cls.up_mid = 0

        cls.info_json.clear()
        cls.download_json.clear()

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

        # 过滤掉默认章节
        filtered_sections = [section for section in info_data["sections"] if section["title"] != "默认章节"]

        # 如果过滤后没有章节，保留原始章节
        if not filtered_sections:
            filtered_sections = info_data["sections"]

        info_data["sections"] = filtered_sections

        CheeseInfo.url = info_data["share_url"]
        CheeseInfo.title = info_data["title"]
        CheeseInfo.subtitle = info_data["subtitle"]
        CheeseInfo.views = info_data["stat"]["play_desc"]
        CheeseInfo.release = info_data["release_info"]
        CheeseInfo.expiry = info_data["user_status"]["user_expiry_content"]

        # 检查是否有可用的章节和剧集
        if not info_data["sections"] or not info_data["sections"][0].get("episodes"):
            raise GlobalException(message="该课程暂无可用内容或章节为空", code=StatusCode.CallError.value)

        CheeseInfo.ep_id = info_data["sections"][0]["episodes"][0]["id"]

        CheeseInfo.up_name = info_data["up_info"]["uname"]
        CheeseInfo.up_mid = info_data["up_info"]["mid"]

        CheeseInfo.info_json = info_data.copy()

        self.parse_episodes()

    @classmethod
    def get_cheese_available_media_info(cls, qn: int = None):
        params = {
            "avid": CheeseInfo.aid,
            "ep_id": CheeseInfo.ep_id,
            "cid": CheeseInfo.cid,
            "fnver": 0,
            "fnval": 4048,
            "fourk": 1
        }

        if qn: params["qn"] = qn

        url = f"https://api.bilibili.com/pugv/player/web/playurl?{cls.url_encode(params)}"

        resp = cls.request_get(url, headers = RequestUtils.get_headers(sessdata = Config.User.SESSDATA))

        CheeseInfo.download_json = resp["data"].copy()

        if not qn:
            if "dash" in CheeseInfo.download_json:
                AudioInfo.get_audio_quality_list(CheeseInfo.download_json["dash"])

                CheeseInfo.stream_type = StreamType.Dash.value

            elif "durl" in CheeseInfo.download_json:
                AudioInfo.get_audio_quality_list({})

                CheeseInfo.stream_type = StreamType.Flv.value

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
