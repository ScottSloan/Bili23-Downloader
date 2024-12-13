import re
import json
import requests
from typing import List, Dict

from utils.tool_v2 import RequestTool, UniversalTool
from utils.config import Config
from utils.error import process_exception, ErrorUtils, VIPError, ParseError, URLError, StatusCode
from utils.mapping import bangumi_type_mapping
from utils.parse.audio import AudioInfo
from utils.parse.extra import ExtraInfo

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

    episodes_list: List = []
    video_quality_id_list: List = []
    video_quality_desc_list: List = []

    sections: Dict = {}
    info_json: Dict = {}

    @staticmethod
    def clear_bangumi_info():
        BangumiInfo.url = BangumiInfo.bvid = BangumiInfo.title = BangumiInfo.cover = BangumiInfo.type_name = ""
        BangumiInfo.epid = BangumiInfo.cid = BangumiInfo.season_id = BangumiInfo.mid = BangumiInfo.type_id = 0

        BangumiInfo.payment = False

        BangumiInfo.episodes_list.clear()
        BangumiInfo.video_quality_id_list.clear()
        BangumiInfo.video_quality_desc_list.clear()

        BangumiInfo.sections.clear()
        BangumiInfo.info_json.clear()

class BangumiParser:
    def __init__(self):
        pass
    
    @process_exception
    def get_epid(self, url: str):
        epid = re.findall(r"ep([0-9]+)", url)

        if not epid:
            raise URLError()

        self.url_type, self.url_type_value = "ep_id", epid[0]

    @process_exception
    def get_season_id(self, url: str):
        season_id = re.findall(r"ss([0-9]+)", url)

        if not season_id:
            raise URLError()

        self.url_type, self.url_type_value, BangumiInfo.season_id = "season_id", season_id[0], season_id[0]

    @process_exception
    def get_mid(self, url: str):
        mid = re.findall(r"md([0-9]*)", url)
        
        if not mid:
            raise URLError()

        req = requests.get(f"https://api.bilibili.com/pgc/review/user?media_id={mid[0]}", headers = RequestTool.get_headers(), proxies = RequestTool.get_proxies(), auth = RequestTool.get_auth(), timeout = 5)
        resp = json.loads(req.text)

        self.check_json(resp)

        BangumiInfo.season_id = resp["result"]["media"]["season_id"]
        self.url_type, self.url_type_value = "season_id", BangumiInfo.season_id

    @process_exception
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
    
    @process_exception
    def get_bangumi_available_media_info(self):
        url = f"https://api.bilibili.com/pgc/player/web/playurl?bvid={BangumiInfo.bvid}&cid={BangumiInfo.cid}&qn=0&fnver=0&fnval=12240&fourk=1"

        req = requests.get(url, headers = RequestTool.get_headers(referer_url = "https://www.bilibili.com", sessdata = Config.User.sessdata), proxies = RequestTool.get_proxies(), auth = RequestTool.get_auth(), timeout = 5)
        resp = json.loads(req.text)

        self.check_json(resp)
            
        info = resp["result"]
        
        # 检测是否为试看内容
        if "dash" not in info:
            raise VIPError()

        BangumiInfo.video_quality_id_list = info["accept_quality"]
        BangumiInfo.video_quality_desc_list = info["accept_description"]

        AudioInfo.get_audio_quality_list(info["dash"])

        ExtraInfo.get_danmaku = Config.Extra.get_danmaku
        ExtraInfo.danmaku_type = Config.Extra.danmaku_type
        ExtraInfo.get_cover = Config.Extra.get_cover

    @process_exception
    def check_bangumi_can_play(self):
        url = f"https://api.bilibili.com/pgc/player/web/v2/playurl?{self.url_type}={self.url_type_value}"

        req = requests.get(url, headers = RequestTool.get_headers(sessdata = Config.User.sessdata), proxies = RequestTool.get_proxies(), auth = RequestTool.get_auth(), timeout = 5)
        resp = json.loads(req.text)

        self.check_json(resp)

    def get_bangumi_type(self):
        # 识别番组类型
        BangumiInfo.type_name = bangumi_type_mapping.get(BangumiInfo.type_id, "未知")

    def parse_url(self, url: str):
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
    
    def check_json(self, json: Dict):
        # 检查接口返回状态码
        status_code = json["code"]
        message = json["message"]
        error = ErrorUtils()

        if status_code != StatusCode.CODE_0:
            if status_code == StatusCode.CODE_10403 and message == "大会员专享限制":
                # 如果提示大会员专享限制就不用抛出异常，因为和地区限制共用一个状态码 -10403
                return
            
            # 如果请求失败，则抛出 ParseError 异常，由 process_exception 进一步处理
            raise ParseError(error.getStatusInfo(status_code), status_code)

    def parse_episodes(self):
        def _parse_main_episodes():
            # 解析正片
            if "seasons" in BangumiInfo.info_json and BangumiInfo.info_json["seasons"]:
                seasons_info = BangumiInfo.info_json["seasons"]

                for season_entry in seasons_info:
                    if season_entry["media_id"] == BangumiInfo.mid:
                        season_title = season_entry["season_title"]
                
            else:
                season_title = "正片"

            BangumiInfo.sections[season_title] = BangumiInfo.episodes_list

        BangumiInfo.sections.clear()

        match Config.Misc.episode_display_mode:
            case Config.Type.EPISODES_SINGLE:
                # 解析单个视频

                # 先解析其他相关视频
                if "section" in BangumiInfo.info_json:
                    extra_episodes = []

                    for section_entry in BangumiInfo.info_json["section"]:
                        extra_episodes += section_entry["episodes"]

                    temp_episodes = BangumiInfo.episodes_list.copy()
                    temp_episodes += extra_episodes

                match self.url_type:
                    case "ep_id":
                        for entry in temp_episodes:
                            if entry["ep_id"] == int(self.url_type_value):
                                BangumiInfo.sections["视频"] = [entry]
                                break

                    case "season_id":
                        # 对于 ssid，默认获取第一集
                        BangumiInfo.sections["视频"] = [BangumiInfo.episodes_list[0]]

            case Config.Type.EPISODES_IN_SECTION:
                # 解析视频所在集合

                match self.url_type:
                    case "ep_id":
                        # 判断视频是否在正片中
                        for episode_entry in BangumiInfo.episodes_list:
                            if episode_entry["ep_id"] == int(self.url_type_value):
                                # 解析正片
                                _parse_main_episodes()
                                break

                        # 判断视频是否在其他集合中
                        if "section" in BangumiInfo.info_json:
                            info_section = BangumiInfo.info_json["section"]

                            for section_entry in info_section:
                                section_title = section_entry["title"]
                                info_episodes = section_entry["episodes"]

                                for episode_entry in info_episodes:
                                    if episode_entry["ep_id"] == int(self.url_type_value):
                                        # 解析此部分内容
                                        for index, value in enumerate(info_episodes):
                                            value["title"] = str(index + 1)

                                        BangumiInfo.sections[section_title] = info_episodes
                                        break
                
                    case "season_id":
                        # 对于 ssid，默认获取正片列表
                        _parse_main_episodes()

            case Config.Type.EPISODES_ALL_SECTIONS:
                # 解析视频所有集合

                # 先解析正片
                _parse_main_episodes()

                # 再解析其他内容
                if "section" in BangumiInfo.info_json:
                    info_section = BangumiInfo.info_json["section"]

                    for section_entry in info_section:
                        section_title = section_entry["title"]
                        section_episodes = section_entry["episodes"]

                        for index, value in enumerate(section_episodes):
                            value["title"] = str(index + 1)

                        BangumiInfo.sections[section_title] = section_episodes

    def clear_bangumi_info(self):
        # 清除番组信息
        BangumiInfo.clear_bangumi_info()

        # 重置音质信息
        AudioInfo.clear_audio_info()

        # 重置附加内容信息
        ExtraInfo.clear_extra_info()
