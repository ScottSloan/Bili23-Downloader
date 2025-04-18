import re
import json

from utils.common.enums import StatusCode, StreamType
from utils.tool_v2 import RequestTool, UniversalTool
from utils.common.exception import GlobalException
from utils.common.data_type import ParseCallback
from utils.parse.episode import EpisodeInfo, EpisodeManager
from utils.parse.audio import AudioInfo
from utils.config import Config

class CheeseInfo:
    url: str = ""
    aid: int = 0
    epid: int = 0
    cid: int = 0
    season_id: int = 0

    title: str = ""
    subtitle: str = ""
    views: str = ""
    release: str = ""
    expiry: str = ""

    stream_type: str = ""

    episodes_list: list = []
    video_quality_id_list: list = []
    video_quality_desc_list: list = []

    up_name: str = ""
    up_mid: int = 0

    info_json: dict = {}
    download_json: dict = {}

    @staticmethod
    def clear_cheese_info():
        CheeseInfo.url = ""
        CheeseInfo.title = ""
        CheeseInfo.subtitle = ""
        CheeseInfo.views = 0
        CheeseInfo.release = ""
        CheeseInfo.expiry = ""
        CheeseInfo.aid = 0
        CheeseInfo.epid = 0
        CheeseInfo.cid = 0
        CheeseInfo.season_id = 0
        CheeseInfo.up_name = ""
        CheeseInfo.up_mid = 0

        CheeseInfo.episodes_list.clear()
        CheeseInfo.video_quality_id_list.clear()
        CheeseInfo.video_quality_desc_list.clear()

        CheeseInfo.info_json.clear()
        CheeseInfo.download_json.clear()

class CheeseParser:
    def __init__(self, callback: ParseCallback):
        self.callback = callback

    def get_epid(self, url: str):
        epid = re.findall(r"ep([0-9]+)", url)

        if not epid:
            raise GlobalException(code = StatusCode.URL.value)

        self.url_type, self.url_type_value = "ep_id", epid[0]

    def get_season_id(self, url: str):
        season_id = re.findall(r"ss([0-9]+)", url)

        if not season_id:
            raise GlobalException(code = StatusCode.URL.value)

        self.url_type, self.url_type_value, CheeseInfo.season_id = "season_id", season_id[0], season_id[0]

    def get_cheese_info(self):
        url = f"https://api.bilibili.com/pugv/view/web/season?{self.url_type}={self.url_type_value}"

        req = RequestTool.request_get(url, headers = RequestTool.get_headers(sessdata = Config.User.SESSDATA))
        resp = json.loads(req.text)

        self.check_json(resp)

        info_data = CheeseInfo.info_json = resp["data"]

        CheeseInfo.url = info_data["share_url"]
        CheeseInfo.title = info_data["title"]
        CheeseInfo.subtitle = info_data["subtitle"]
        CheeseInfo.views = info_data["stat"]["play_desc"]
        CheeseInfo.release = info_data["release_info"]
        CheeseInfo.expiry = info_data["user_status"]["user_expiry_content"]

        CheeseInfo.episodes_list = info_data["episodes"]
        CheeseInfo.epid = CheeseInfo.episodes_list[0]["id"]

        CheeseInfo.up_name = info_data["up_info"]["uname"]
        CheeseInfo.up_mid = info_data["up_info"]["mid"]

        self.parse_episodes()

    def get_cheese_available_media_info(self):
        url = f"https://api.bilibili.com/pugv/player/web/playurl?avid={CheeseInfo.aid}&ep_id={CheeseInfo.epid}&cid={CheeseInfo.cid}&fnver=0&fnval=4048&fourk=1"

        req = RequestTool.request_get(url, headers = RequestTool.get_headers(sessdata = Config.User.SESSDATA))
        resp = json.loads(req.text)

        self.check_json(resp)

        CheeseInfo.download_json = info = resp["data"]

        CheeseInfo.video_quality_id_list = info["accept_quality"]
        CheeseInfo.video_quality_desc_list = info["accept_description"]
        
        if "dash" in info:
            AudioInfo.get_audio_quality_list(info["dash"])

            CheeseInfo.stream_type = StreamType.Dash.value

        elif "durl" in info:
            AudioInfo.get_audio_quality_list({})

            CheeseInfo.stream_type = StreamType.Flv.value

    def parse_url(self, url: str):
        def worker():
            self.clear_cheese_info()

            match UniversalTool.re_find_string(r"ep|ss", url):
                case "ep":
                    self.get_epid(url)

                case "ss":
                    self.get_season_id(url)

            self.get_cheese_info()

            self.get_cheese_available_media_info()

            return StatusCode.Success.value

        try:
            return worker()

        except Exception as e:
            raise GlobalException(callback = self.callback.onError) from e
    
    def check_json(self, data: dict):
        # 检查接口返回状态码
        status_code = data["code"]

        if status_code != StatusCode.Success.value:
            raise GlobalException(message = data["message"], code = status_code)

    def parse_episodes(self):
        EpisodeInfo.clear_episode_data()

        if self.url_type == "season_id":
            ep_id = CheeseInfo.epid
        else:
            ep_id = int(self.url_type_value)

        EpisodeManager.cheese_episode_parser(CheeseInfo.info_json, ep_id)

    def clear_cheese_info(self):
        CheeseInfo.clear_cheese_info()

        AudioInfo.clear_audio_info()
