import re
import json
import requests

from utils.tools import get_header, get_auth, get_proxy, find_str
from utils.config import Config, Audio
from utils.error import process_exception, ErrorUtils, VIPError, ParseError, URLError, StatusCode

class BangumiInfo:
    url: str = ""
    bvid: str = ""
    epid = cid = season_id = mid = None

    title = cover = type = resolution = None

    payment = False

    episodes = resolution_id = resolution_desc = []

    sections = {}

class BangumiParser:
    def __init__(self, onError):
        self.onError = onError
    
    @process_exception
    def get_epid(self, url):
        epid = re.findall(r"ep([0-9]+)", url)

        if not epid:
            raise URLError()

        self.argument, self.value = "ep_id", epid[0]

    @process_exception
    def get_season_id(self, url):
        season_id = re.findall(r"ss([0-9]+)", url)

        if not season_id:
            raise URLError()

        self.argument, self.value, BangumiInfo.season_id = "season_id", season_id[0], season_id[0]

    @process_exception
    def get_mid(self, url):
        mid = re.findall(r"md([0-9]*)", url)
        
        if not mid:
            self.onError(101)

        req = requests.get(f"https://api.bilibili.com/pgc/review/user?media_id={mid[0]}", headers = get_header(), proxies = get_proxy(), auth = get_auth(), timeout = 8)
        resp = json.loads(req.text)

        self.check_json(resp)

        BangumiInfo.season_id = resp["result"]["media"]["season_id"]
        self.argument, self.value = "season_id", BangumiInfo.season_id

    @process_exception
    def get_bangumi_info(self):
        url = f"https://api.bilibili.com/pgc/view/web/season?{self.argument}={self.value}"

        req = requests.get(url, headers = get_header(), proxies = get_proxy(), auth = get_auth(), timeout = 8)
        resp = json.loads(req.text)

        self.check_json(resp)
        
        info_result = resp["result"]

        BangumiInfo.url = info_result["episodes"][0]["link"]
        BangumiInfo.title = info_result["title"]

        BangumiInfo.payment = True if "payment" in info_result else False
        
        BangumiInfo.episodes = info_result["episodes"]

        BangumiInfo.url = BangumiInfo.episodes[0]["link"]
        BangumiInfo.bvid = BangumiInfo.episodes[0]["bvid"]
        BangumiInfo.cid = BangumiInfo.episodes[0]["cid"]
        BangumiInfo.epid = BangumiInfo.episodes[0]["id"]

        BangumiInfo.mid = info_result["media_id"]

        BangumiInfo.sections.clear()

        # 剧集列表解析方式
        match Config.Misc.show_episodes:
            case Config.Type.EPISODES_SINGLE:
                # 解析单个视频

                # 先解析其他相关视频
                if "section" in info_result:
                    extra_episodes = []

                    for section_entry in info_result["section"]:
                        extra_episodes += section_entry["episodes"]

                    BangumiInfo.episodes += extra_episodes

                match self.argument:
                    case "ep_id":
                        for entry in BangumiInfo.episodes.copy():
                            if entry["ep_id"] == int(self.value):
                                BangumiInfo.sections["视频"] = [entry]
                                break

                    case "season_id":
                        # 对于 ssid，默认获取第一集
                        BangumiInfo.sections["视频"] = [info_result["episodes"][0]]

            case Config.Type.EPISODES_IN_SECTION:
                # 解析视频所在集合

                match self.argument:
                    case "ep_id":
                        # 判断视频是否在正片中
                        for episode_entry in BangumiInfo.episodes:
                            if episode_entry["ep_id"] == int(self.value):
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
                                    if episode_entry["ep_id"] == int(self.value):
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

        self.get_bangumi_type(info_result["type"])
    
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

        BangumiInfo.resolution_id = json_data["accept_quality"]
        BangumiInfo.resolution_desc = json_data["accept_description"]

        # 重置音质标识符
        Audio.q_dolby = Audio.q_hires = Audio.q_192k = Audio.q_132k = Audio.q_64k = False

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
                    if entry["id"] == 30280:
                        Audio.q_192k = True
                    
                    if entry["id"] == 30232:
                        Audio.q_132k = True

                    if entry["id"] == 30216:
                        Audio.q_64k = True

        # 存在无损或杜比
        if Audio.q_hires or Audio.q_dolby:
            # 如果选择下载无损或杜比
            if Config.Download.sound_quality == 30250:
                Audio.audio_quality = 30250
            else:
                Audio.audio_quality = Config.Download.sound_quality

        # 否则根据实际所选音质下载
        else:
            Audio.audio_quality = Config.Download.sound_quality

        # 重置仅下载音频标识符
        Audio.audio_only = False

    @process_exception
    def check_bangumi_can_play(self):
        url = f"https://api.bilibili.com/pgc/player/web/v2/playurl?{self.argument}={self.value}"

        req = requests.get(url, headers = get_header(), proxies = get_proxy(), auth = get_auth(), timeout = 8)
        resp = json.loads(req.text)

        self.check_json(resp)

    def get_bangumi_type(self, type_id):
        # 识别类型
        match type_id:
            case 1:
                BangumiInfo.type = "番剧"
            case 2:
                BangumiInfo.type = "电影"
            case 3:
                BangumiInfo.type = "纪录片"
            case 4:
                BangumiInfo.type = "国创"
            case 5:
                BangumiInfo.type = "电视剧"
            case 7:
                BangumiInfo.type = "综艺"

    def parse_url(self, url):
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
    
    def check_json(self, json):
        # 检查接口返回状态码
        status_code = json["code"]
        error = ErrorUtils()

        if status_code != StatusCode.CODE_0:
            # 如果请求失败，则抛出 ParseError 异常，由 process_exception 进一步处理
            raise ParseError(error.getStatusInfo(status_code), status_code)

    def parse_episodes(self, info_result):
        # 解析正片
        if "seasons" in info_result and info_result["seasons"]:
            seasons_info = info_result["seasons"]

            for season_entry in seasons_info:
                if season_entry["media_id"] == BangumiInfo.mid:
                    season_title = season_entry["season_title"]
            
        else:
            season_title = "正片"

        BangumiInfo.sections[season_title] = BangumiInfo.episodes