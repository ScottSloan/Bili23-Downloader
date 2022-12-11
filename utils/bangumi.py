import re
import json
import requests

from .tools import *
from .config import Config
from .api import API

class BangumiInfo:
    url = bvid = title = type = ""

    epid = ssid = mid = cid = quality = 0

    episodes = down_episodes = quality_id = quality_desc = []

    sections = {}

    payment = False

class BangumiParser:
    def __init__(self, onError):
        self.onError = onError
    
    def get_epid(self, url):
        try:
            BangumiInfo.epid = re.findall(r"ep([0-9]*)", url)[0]
        except:
            self.onError(400)
            return

        self.argument, self.value = "ep_id", BangumiInfo.epid

    def get_season_id(self, url):
        try:
            BangumiInfo.ssid = re.findall(r"ss([0-9]*)", url)[0]
        except:
            self.onError(400)
            return

        self.argument, self.value = "season_id", BangumiInfo.ssid

    def get_media_id(self, url):
        try:
            BangumiInfo.mid = re.findall(r"md([0-9]*)", url)[0]
        except:
            self.onError(400)
            return

        url = API.Bangumi.mid_api(BangumiInfo.mid)

        media_request = requests.get(url, headers = get_header(), proxies = get_proxy(), auth = get_auth())
        media_json = json.loads(media_request.text)

        if self.check_json(media_json): return

        BangumiInfo.ssid = media_json["result"]["media"]["season_id"]
        self.argument, self.value = "season_id", BangumiInfo.ssid
    
    def get_bangumi_info(self):
        url = API.Bangumi.info_api(self.argument, self.value)

        info_request = requests.get(url, headers = get_header(), proxies = get_proxy(), auth = get_auth())
        info_json = json.loads(info_request.text)

        if self.check_json(info_json): return
        
        info_result = info_json["result"]
        BangumiInfo.url = info_result["episodes"][0]["link"]
        BangumiInfo.title = info_result["title"]

        BangumiInfo.payment = True if "payment" in info_result else False
        
        BangumiInfo.episodes = info_result["episodes"]
        BangumiInfo.sections["正片"] = BangumiInfo.episodes

        if "section" in info_result and Config.show_sections:
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
        if type_id == 1:
            BangumiInfo.type = "番剧"
        elif type_id == 2:
            BangumiInfo.type = "电影"
        elif type_id == 3:
            BangumiInfo.type = "纪录片"
        elif type_id == 4:
            BangumiInfo.type = "国创"
        elif type_id == 5:
            BangumiInfo.type = "电视剧"
        elif type_id == 7:
            BangumiInfo.type = "综艺"

    def get_bangumi_quality(self):
        url = API.Bangumi.download_api(BangumiInfo.bvid, BangumiInfo.cid)

        bangumi_request = requests.get(url, headers = get_header(BangumiInfo.url, cookie = Config.user_sessdata), proxies = get_proxy(), auth = get_auth())
        bangumi_json = json.loads(bangumi_request.text)
        
        if self.check_json(bangumi_json): return

        json_data = bangumi_json["result"]

        BangumiInfo.quality_id = json_data["accept_quality"]
        BangumiInfo.quality_desc = json_data["accept_description"]

    def parse_url(self, url):
        if "ep" in url:
            self.get_epid(url)
        elif "ss" in url:
            self.get_season_id(url)
        elif "md" in url:
            self.get_media_id(url)
        
        self.get_bangumi_info()
        self.get_bangumi_quality()
        
    def check_json(self, json):  
        if json["code"] != 0:
            self.onError(400)
            return True
            