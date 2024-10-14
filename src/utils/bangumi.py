import re
import json
import requests
from typing import List, Dict

from utils.tools import get_header, get_auth, get_proxy, find_str
from utils.config import Config, Audio
from utils.error import process_exception, ErrorUtils, VIPError, ParseError, URLError, StatusCode
from utils.mapping import bangumi_type_mapping

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

        req = requests.get(f"https://api.bilibili.com/pgc/review/user?media_id={mid[0]}", headers = get_header(), proxies = get_proxy(), auth = get_auth(), timeout = 8)
        resp = json.loads(req.text)

        self.check_json(resp)

        BangumiInfo.season_id = resp["result"]["media"]["season_id"]
        self.url_type, self.url_type_value = "season_id", BangumiInfo.season_id

    @process_exception
    def get_bangumi_info(self):
        # 获取番组信息
        url = f"https://api.bilibili.com/pgc/view/web/season?{self.url_type}={self.url_type_value}"

        req = requests.get(url, headers = get_header(), proxies = get_proxy(), auth = get_auth(), timeout = 8)
        resp = json.loads(req.text)

        self.check_json(resp)
        
        info_result = resp["result"]

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

        # 剧集列表解析方式
        match Config.Misc.show_episodes:
            case Config.Type.EPISODES_SINGLE:
                # 解析单个视频

                # 先解析其他相关视频
                if "section" in info_result:
                    extra_episodes = []

                    for section_entry in info_result["section"]:
                        extra_episodes += section_entry["episodes"]

                    BangumiInfo.episodes_list += extra_episodes

                match self.url_type:
                    case "ep_id":
                        for entry in BangumiInfo.episodes_list.copy():
                            if entry["ep_id"] == int(self.url_type_value):
                                BangumiInfo.sections["视频"] = [entry]
                                break

                    case "season_id":
                        # 对于 ssid，默认获取第一集
                        BangumiInfo.sections["视频"] = [info_result["episodes"][0]]

            case Config.Type.EPISODES_IN_SECTION:
                # 解析视频所在集合

                match self.url_type:
                    case "ep_id":
                        # 判断视频是否在正片中
                        for episode_entry in BangumiInfo.episodes_list:
                            if episode_entry["ep_id"] == int(self.url_type_value):
                                # 解析正片
                                self.parse_episodes(info_result)
                                break

                        # 判断视频是否在其他集合中
                        if "section" in info_result:
                            info_section = info_result["section"]

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
                        self.parse_episodes(info_result)

            case Config.Type.EPISODES_ALL_SECTIONS:
                # 解析视频所有集合

                # 先解析正片
                self.parse_episodes(info_result)

                # 再解析其他内容
                if "section" in info_result:
                    info_section = info_result["section"]

                    for section_entry in info_section:
                        section_title = section_entry["title"]
                        section_episodes = section_entry["episodes"]

                        for index, value in enumerate(section_episodes):
                            value["title"] = str(index + 1)

                        BangumiInfo.sections[section_title] = section_episodes

        self.get_bangumi_type()
    
    @process_exception
    def get_bangumi_resolution(self):
        url = f"https://api.bilibili.com/pgc/player/web/playurl?bvid={BangumiInfo.bvid}&cid={BangumiInfo.cid}&qn=0&fnver=0&fnval=12240&fourk=1"

        req = requests.get(url, headers = get_header(referer_url= "https://www.bilibili.com", cookie = Config.User.sessdata), proxies = get_proxy(), auth = get_auth(), timeout = 8)
        resp = json.loads(req.text)

        self.check_json(resp)
            
        json_data = resp["result"]
        
        # 检测是否为试看内容
        if "dash" not in json_data:
            raise VIPError()

        BangumiInfo.video_quality_id_list = json_data["accept_quality"]
        BangumiInfo.video_quality_desc_list = json_data["accept_description"]

        # 检测无损或杜比是否存在
        if "flac" in json_data["dash"]:
            if json_data["dash"]["flac"]:
                Audio.q_hires = True

        if "dolby" in json_data["dash"]:
            if json_data["dash"]["dolby"]["audio"]:
                Audio.q_dolby = True

        # 检测 192k, 132k, 64k 音质是否存在
        if "audio" in json_data["dash"]:
            if json_data["dash"]["audio"]:
                for entry in json_data["dash"]["audio"]:
                    match entry["id"]:
                        case 30280:
                            Audio.q_192k = True
                    
                        case 30232:
                            Audio.q_132k = True

                        case 30216:
                            Audio.q_64k = True

            Audio.audio_quality_id = Config.Download.audio_quality_id

    @process_exception
    def check_bangumi_can_play(self):
        url = f"https://api.bilibili.com/pgc/player/web/v2/playurl?{self.url_type}={self.url_type_value}"

        req = requests.get(url, headers = get_header(), proxies = get_proxy(), auth = get_auth(), timeout = 8)
        resp = json.loads(req.text)

        self.check_json(resp)

    def get_bangumi_type(self):
        # 识别番组类型
        BangumiInfo.type_name = bangumi_type_mapping.get(BangumiInfo.type_id, "未知")

    def parse_url(self, url: str):
        # 清除当前的番组信息
        self.clear_bangumi_info()

        match find_str(r"ep|ss|md", url):
            case "ep":
                self.get_epid(url)

            case "ss":
                self.get_season_id(url)

            case "md":
                self.get_mid(url)

        # 先检查视频是否存在区域限制
        self.check_bangumi_can_play()

        self.get_bangumi_info()
        self.get_bangumi_resolution()
    
    def check_json(self, json: Dict):
        # 检查接口返回状态码
        status_code = json["code"]
        error = ErrorUtils()

        if status_code != StatusCode.CODE_0:
            # 如果请求失败，则抛出 ParseError 异常，由 process_exception 进一步处理
            raise ParseError(error.getStatusInfo(status_code), status_code)

    def parse_episodes(self, info_result: Dict):
        # 解析正片
        if "seasons" in info_result and info_result["seasons"]:
            seasons_info = info_result["seasons"]

            for season_entry in seasons_info:
                if season_entry["media_id"] == BangumiInfo.mid:
                    season_title = season_entry["season_title"]
            
        else:
            season_title = "正片"

        BangumiInfo.sections[season_title] = BangumiInfo.episodes_list

    def clear_bangumi_info(self):
        # 清除当前的番组信息
        BangumiInfo.url = BangumiInfo.bvid = BangumiInfo.title = BangumiInfo.cover = BangumiInfo.type_name = ""
        BangumiInfo.epid = BangumiInfo.cid = BangumiInfo.season_id = BangumiInfo.mid = BangumiInfo.type_id = 0

        BangumiInfo.payment = False

        BangumiInfo.episodes_list.clear()
        BangumiInfo.video_quality_id_list.clear()
        BangumiInfo.video_quality_desc_list.clear()

        BangumiInfo.sections.clear()

        # 重置音质信息
        Audio.q_hires = Audio.q_dolby = Audio.q_192k = Audio.q_132k = Audio.q_64k = Audio.audio_only = False
        Audio.audio_quality_id = 0