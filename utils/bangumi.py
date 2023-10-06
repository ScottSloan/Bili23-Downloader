import re
import json
import requests

from .tools import *
from .config import Config

class BangumiInfo:
    url = bvid = epid = cid = season_id = mid = None

    title = cover = type = resolution = None

    payment = False

    episodes = resolution_id = resolution_desc = []

    sections = {}

class BangumiParser:
    def __init__(self, onError):
        self.onError = onError
    
    def get_epid(self, url):
        epid = re.findall(r"ep([0-9]+)", url)

        if not epid: self.onError(101)

        self.argument, self.value = "ep_id", epid[0]

    def get_season_id(self, url):
        season_id = re.findall(r"ss([0-9]+)", url)

        if not season_id: self.onError(101)

        self.argument, self.value, BangumiInfo.season_id = "season_id", season_id[0], season_id[0]

    def get_mid(self, url):
        mid = re.findall(r"md([0-9]*)", url)
        
        if not mid: self.onError(101)

        req = requests.get(f"https://api.bilibili.com/pgc/review/user?media_id={mid[0]}", headers = get_header(), proxies = get_proxy(), auth = get_auth())
        resp = json.loads(req.text)

        self.check_json(resp, 101)

        BangumiInfo.season_id = resp["result"]["media"]["season_id"]
        self.argument, self.value = "season_id", BangumiInfo.season_id

    def get_bangumi_info(self):
        url = f"https://api.bilibili.com/pgc/view/web/season?{self.argument}={self.value}"

        req = requests.get(url, headers = get_header(), proxies = get_proxy(), auth = get_auth(), timeout = 8)
        resp = json.loads(req.text)

        self.check_json(resp, 101)
        
        info_result = resp["result"]

        BangumiInfo.url = info_result["episodes"][0]["link"]
        BangumiInfo.title = info_result["title"]

        BangumiInfo.payment = True if "payment" in info_result else False
        
        BangumiInfo.episodes = info_result["episodes"]
        BangumiInfo.sections["正片"] = BangumiInfo.episodes

        if "section" in info_result and Config.Misc.show_sections:
            info_section = info_result["section"]

            for section in info_section:
                section_title = section["title"]
                section_episodes = section["episodes"]

                for index, value in enumerate(section_episodes):
                    value["title"] = str(index + 1)

                BangumiInfo.sections[section_title] = section_episodes

        BangumiInfo.url = BangumiInfo.episodes[0]["link"]
        BangumiInfo.bvid = BangumiInfo.episodes[0]["bvid"]
        BangumiInfo.cid = BangumiInfo.episodes[0]["cid"]
        BangumiInfo.epid = BangumiInfo.episodes[0]["id"]

        self.get_bangumi_type(info_result["type"])

    def get_bangumi_type(self, type_id):
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
            case 6:
                BangumiInfo.type = "Unknown"
            case 7:
                BangumiInfo.type = "综艺"

    def get_bangumi_resolution(self):
        url = f"https://api.bilibili.com/pgc/player/web/playurl?bvid={BangumiInfo.bvid}&cid={BangumiInfo.cid}&qn=0&fnver=0&fnval=4048&fourk=1"

        req = requests.get(url, headers = get_header(BangumiInfo.url, Config.User.sessdata), proxies = get_proxy(), auth = get_auth(), timeout = 8)
        resp = json.loads(req.text)

        self.check_json(resp, 102)
        
        json_data = resp["result"]

        BangumiInfo.resolution_id = json_data["accept_quality"]
        BangumiInfo.resolution_desc = json_data["accept_description"]

    def parse_url(self, url):
        if "ep" in url:
            self.get_epid(url)
        elif "ss" in url:
            self.get_season_id(url)
        elif "md" in url:
            self.get_mid(url)

        self.get_bangumi_info()
        self.get_bangumi_resolution()
    
    def check_json(self, json, err_code):
        if json["code"] != 0:
            self.onError(err_code)