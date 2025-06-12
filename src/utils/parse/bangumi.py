from utils.tool_v2 import UniversalTool, FormatTool
from utils.config import Config

from utils.common.exception import GlobalException
from utils.common.map import bangumi_type_map
from utils.common.enums import StatusCode, StreamType
from utils.common.data_type import ParseCallback
from utils.common.request import RequestUtils

from utils.parse.audio import AudioInfo
from utils.parse.episode import EpisodeInfo, EpisodeManager
from utils.parse.parser import Parser

class BangumiInfo:
    url: str = ""
    bvid: str = ""
    epid: int = 0 
    cid: int = 0
    season_id: int = 0
    mid: int = 0

    title: str = ""
    cover: str = ""
    views: str = ""
    danmakus: str = ""
    followers: str = ""
    styles: str = ""
    new_ep: str = ""
    actors: str = ""
    evaluate: str = ""

    type_id: int = 0
    type_name: str = ""

    payment: bool = False

    stream_type: int = 0

    episodes_list: list = []
    video_quality_id_list: list = []
    video_quality_desc_list: list = []

    area: str = ""
    up_name: str = ""
    up_mid: int = 0

    info_json: dict = {}
    download_json: dict = {}

    @classmethod
    def clear_bangumi_info(cls):
        cls.url = ""
        cls.bvid = ""
        cls.title = ""
        cls.cover = ""
        cls.type_name = ""
        cls.views = 0
        cls.danmakus = 0
        cls.followers = 0
        cls.styles = 0
        cls.new_ep = ""
        cls.actors = ""
        cls.evaluate = ""
        cls.epid = 0
        cls.cid = 0
        cls.season_id = 0
        cls.mid = 0
        cls.type_id = 0
        cls.stream_type = 0
        cls.area = ""
        cls.up_name = ""
        cls.up_mid = 0

        cls.payment = False

        cls.episodes_list.clear()
        cls.video_quality_id_list.clear()
        cls.video_quality_desc_list.clear()

        cls.info_json.clear()
        cls.download_json.clear()

class BangumiParser(Parser):
    def __init__(self, callback: ParseCallback):
        super().__init__()

        self.callback = callback
    
    def get_epid(self, url: str):
        epid = self.re_find_str(r"ep([0-9]+)", url)

        self.url_type, self.url_type_value = "ep_id", epid[0]

    def get_season_id(self, url: str):
        season_id = self.re_find_str(r"ss([0-9]+)", url)

        self.url_type, self.url_type_value, BangumiInfo.season_id = "season_id", season_id[0], season_id[0]

    def get_mid(self, url: str):
        mid = self.re_find_str(r"md([0-9]*)", str)

        url = f"https://api.bilibili.com/pgc/review/user?media_id={mid[0]}"

        resp = self.request_get(url, headers = RequestUtils.get_headers(referer_url = self.bilibili_url, sessdata = Config.User.SESSDATA))

        BangumiInfo.season_id = resp["result"]["media"]["season_id"]
        self.url_type, self.url_type_value = "season_id", BangumiInfo.season_id

    def get_bangumi_info(self):
        # 获取番组信息
        url = f"https://api.bilibili.com/pgc/view/web/season?{self.url_type}={self.url_type_value}"

        resp = self.request_get(url, headers = RequestUtils.get_headers(referer_url = self.bilibili_url, sessdata = Config.User.SESSDATA))
        
        info_result = BangumiInfo.info_json = resp["result"]

        BangumiInfo.payment = True if "payment" in info_result else False
        
        BangumiInfo.episodes_list = info_result["episodes"]

        BangumiInfo.title = info_result["title"]
        BangumiInfo.url = BangumiInfo.episodes_list[0]["link"]
        BangumiInfo.bvid = BangumiInfo.episodes_list[0]["bvid"]
        BangumiInfo.cid = BangumiInfo.episodes_list[0]["cid"]
        BangumiInfo.epid = BangumiInfo.episodes_list[0]["id"]
        BangumiInfo.mid = info_result["media_id"]

        BangumiInfo.type_id = info_result["type"]

        BangumiInfo.cover = info_result["cover"]
        BangumiInfo.views = info_result["icon_font"]["text"]
        BangumiInfo.danmakus = FormatTool.format_data_count(info_result["stat"]["danmakus"])
        BangumiInfo.followers = info_result["stat"]["follow_text"]
        BangumiInfo.styles = " / ".join(info_result["styles"])
        BangumiInfo.new_ep = info_result["new_ep"]["desc"]
        BangumiInfo.actors = info_result["actors"].replace("\n", " ")
        BangumiInfo.evaluate = info_result["evaluate"]

        BangumiInfo.area = info_result["areas"][0]["name"]

        if "up_info" in info_result:
            BangumiInfo.up_name = info_result["up_info"]["uname"]
            BangumiInfo.up_mid = info_result["up_info"]["mid"]

        self.parse_episodes()

        self.get_bangumi_type()
    
    def get_bangumi_available_media_info(self):
        url = f"https://api.bilibili.com/pgc/player/web/playurl?bvid={BangumiInfo.bvid}&cid={BangumiInfo.cid}&fnver=0&fnval=12240&fourk=1"

        resp = self.request_get(url, headers = RequestUtils.get_headers(referer_url = self.bilibili_url, sessdata = Config.User.SESSDATA))

        BangumiInfo.download_json = info = resp["result"]

        if "dash" in info:
            AudioInfo.get_audio_quality_list(info["dash"])

            BangumiInfo.stream_type = StreamType.Dash.value
        
        elif "durl" in info:
            AudioInfo.get_audio_quality_list({})

            BangumiInfo.stream_type = StreamType.Flv.value
        
        else:
            code = StatusCode.Pay.value if BangumiInfo.payment and Config.User.login else StatusCode.Vip.value

            raise GlobalException(code = code)
                
        BangumiInfo.video_quality_id_list = info["accept_quality"]
        BangumiInfo.video_quality_desc_list = info["accept_description"]

    def check_bangumi_can_play(self):
        url = f"https://api.bilibili.com/pgc/player/web/v2/playurl?{self.url_type}={self.url_type_value}"

        self.request_get(url, headers = RequestUtils.get_headers(referer_url = self.bilibili_url, sessdata = Config.User.SESSDATA))

    def get_bangumi_type(self):
        BangumiInfo.type_name = bangumi_type_map.get(BangumiInfo.type_id, "未知")

    def parse_url(self, url: str):
        def worker():
            # 清除当前的番组信息
            self.clear_bangumi_info()

            match UniversalTool.re_find_string(r"ep|ss|md", url):
                case "ep":
                    self.get_epid(url)

                case "ss":
                    self.get_season_id(url)

                case "md":
                    self.get_mid(url)

            # 先检查视频是否存在区域限制
            self.check_bangumi_can_play()

            self.get_bangumi_info()
            self.get_bangumi_available_media_info()

            return StatusCode.Success.value

        try:
            return worker()

        except Exception as e:
            raise GlobalException(callback = self.callback.onError) from e
    
    def check_json(self, data: dict):
        status_code = data["code"]
        message = data["message"]

        if status_code != StatusCode.Success.value:
            if status_code == StatusCode.Area_Limit.value and message == "大会员专享限制":
                return
            
            raise GlobalException(message = message, code = status_code)

    def parse_episodes(self):
        EpisodeInfo.clear_episode_data()

        if self.url_type == "season_id":
            ep_id = BangumiInfo.epid
        else:
            ep_id = int(self.url_type_value)

        EpisodeManager.bangumi_episodes_parser(BangumiInfo.info_json, ep_id)

    def clear_bangumi_info(self):
        # 清除番组信息
        BangumiInfo.clear_bangumi_info()

        # 重置音质信息
        AudioInfo.clear_audio_info()
