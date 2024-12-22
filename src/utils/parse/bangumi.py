import re
import json
import requests

from utils.tool_v2 import RequestTool, UniversalTool
from utils.config import Config
from utils.common.exception import GlobalException
from utils.common.map import bangumi_type_map
from utils.parse.audio import AudioInfo
from utils.parse.extra import ExtraInfo
from utils.parse.episode import EpisodeInfo, bangumi_episodes_parser
from utils.common.enums import StatusCode
from utils.common.data_type import ParseCallback

class BangumiInfo:
    url: str = ""
    bvid: str = ""
    epid: int = 0 
    cid: int = 0
    season_id: int = 0
    mid: int = 0

    title: str = ""
    cover: str = ""

    type_id: int = 0
    type_name: str = ""

    payment: bool = False

    episodes_list: list = []
    video_quality_id_list: list = []
    video_quality_desc_list: list = []

    info_json: dict = {}

    @staticmethod
    def clear_bangumi_info():
        BangumiInfo.url = BangumiInfo.bvid = BangumiInfo.title = BangumiInfo.cover = BangumiInfo.type_name = ""
        BangumiInfo.epid = BangumiInfo.cid = BangumiInfo.season_id = BangumiInfo.mid = BangumiInfo.type_id = 0

        BangumiInfo.payment = False

        BangumiInfo.episodes_list.clear()
        BangumiInfo.video_quality_id_list.clear()
        BangumiInfo.video_quality_desc_list.clear()

        BangumiInfo.info_json.clear()

class BangumiParser:
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

        self.url_type, self.url_type_value, BangumiInfo.season_id = "season_id", season_id[0], season_id[0]

    def get_mid(self, url: str):
        mid = re.findall(r"md([0-9]*)", url)
        
        if not mid:
            raise Exception(StatusCode.URL.value)

        req = requests.get(f"https://api.bilibili.com/pgc/review/user?media_id={mid[0]}", headers = RequestTool.get_headers(), proxies = RequestTool.get_proxies(), auth = RequestTool.get_auth(), timeout = 5)
        resp = json.loads(req.text)

        self.check_json(resp)

        BangumiInfo.season_id = resp["result"]["media"]["season_id"]
        self.url_type, self.url_type_value = "season_id", BangumiInfo.season_id

    def get_bangumi_info(self):
        # 获取番组信息
        url = f"https://api.bilibili.com/pgc/view/web/season?{self.url_type}={self.url_type_value}"

        req = requests.get(url, headers = RequestTool.get_headers(), proxies = RequestTool.get_proxies(), auth = RequestTool.get_auth(), timeout = 5)
        resp = json.loads(req.text)

        self.check_json(resp)
        
        info_result = BangumiInfo.info_json = resp["result"]

        BangumiInfo.url = info_result["episodes"][0]["link"]
        BangumiInfo.title = info_result["title"]

        BangumiInfo.payment = True if "payment" in info_result else False
        
        BangumiInfo.episodes_list = info_result["episodes"]

        BangumiInfo.url = BangumiInfo.episodes_list[0]["link"]
        BangumiInfo.bvid = BangumiInfo.episodes_list[0]["bvid"]
        BangumiInfo.cid = BangumiInfo.episodes_list[0]["cid"]
        BangumiInfo.epid = BangumiInfo.episodes_list[0]["id"]
        BangumiInfo.mid = info_result["media_id"]

        BangumiInfo.type_id = info_result["type"]

        self.parse_episodes()

        self.get_bangumi_type()
    
    def get_bangumi_available_media_info(self):
        url = f"https://api.bilibili.com/pgc/player/web/playurl?bvid={BangumiInfo.bvid}&cid={BangumiInfo.cid}&qn=0&fnver=0&fnval=12240&fourk=1"

        req = requests.get(url, headers = RequestTool.get_headers(referer_url = "https://www.bilibili.com", sessdata = Config.User.sessdata), proxies = RequestTool.get_proxies(), auth = RequestTool.get_auth(), timeout = 5)
        resp = json.loads(req.text)

        self.check_json(resp)
            
        info = resp["result"]
        
        # 检测是否为试看内容
        if "dash" not in info:
            if BangumiInfo.payment and Config.User.login:
                raise Exception(StatusCode.Pay.value)
            else:
                raise Exception(StatusCode.Vip.value)

        BangumiInfo.video_quality_id_list = info["accept_quality"]
        BangumiInfo.video_quality_desc_list = info["accept_description"]

        AudioInfo.get_audio_quality_list(info["dash"])

        ExtraInfo.get_danmaku = Config.Extra.get_danmaku
        ExtraInfo.danmaku_type = Config.Extra.danmaku_type
        ExtraInfo.get_subtitle = Config.Extra.get_subtitle
        ExtraInfo.subtitle_type = Config.Extra.subtitle_type
        ExtraInfo.get_cover = Config.Extra.get_cover

    def check_bangumi_can_play(self):
        url = f"https://api.bilibili.com/pgc/player/web/v2/playurl?{self.url_type}={self.url_type_value}"

        req = requests.get(url, headers = RequestTool.get_headers(sessdata = Config.User.sessdata), proxies = RequestTool.get_proxies(), auth = RequestTool.get_auth(), timeout = 5)
        resp = json.loads(req.text)

        self.check_json(resp)

    def get_bangumi_type(self):
        # 识别番组类型
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
            raise GlobalException(e, callback = self.callback.error_callback)
    
    def check_json(self, json: dict):
        # 检查接口返回状态码
        status_code = json["code"]
        message = json["message"]

        if status_code != StatusCode.Success.value:
            if status_code == StatusCode.Area_Limit.value and message == "大会员专享限制":
                # 如果提示大会员专享限制就不用抛出异常，因为和地区限制共用一个状态码 -10403
                return
            
            raise Exception(status_code)

    def parse_episodes(self):
        EpisodeInfo.clear_episode_data()

        if self.url_type == "season_id":
            ep_id = BangumiInfo.epid
        else:
            ep_id = int(self.url_type_value)

        bangumi_episodes_parser(BangumiInfo.info_json, ep_id)

    def clear_bangumi_info(self):
        # 清除番组信息
        BangumiInfo.clear_bangumi_info()

        # 重置音质信息
        AudioInfo.clear_audio_info()

        # 重置附加内容信息
        ExtraInfo.clear_extra_info()
