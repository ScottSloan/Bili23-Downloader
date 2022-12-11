import re
import json
import requests

from .tools import *
from .api import API

class CheeseInfo:
    epid = ssid = avid = cid = 0
    
    url = title = ""

    down_episodes = episodes = quality_id = quality_desc = []

class CheeseParser:
    def __init__(self, onError):
        self.onError = onError
    
    def get_epid(self, url):
        try:
            CheeseInfo.epid = re.findall(r"ep([0-9]*)", url)[0]
        except:
            self.onError(400)
            return

        self.argument, self.value = "ep_id", CheeseInfo.epid

    def get_season_id(self, url):
        try:
            CheeseInfo.ssid = re.findall(r"ss([0-9]*)", url)[0]
        except:
            self.onError(400)
            return

        self.argument, self.value = "season_id", CheeseInfo.ssid

    def get_cheese_info(self):
        url = API.Cheese.info_api(self.argument, self.value)

        info_request = requests.get(url, headers = get_header(), proxies = get_proxy(), auth = get_auth())
        info_json = json.loads(info_request.text)

        if self.check_json(info_json): return

        info_data = info_json["data"]
        CheeseInfo.title = info_data["title"]
        CheeseInfo.url = info_data["share_url"]
        CheeseInfo.episodes = info_data["episodes"]

        info_episode = CheeseInfo.episodes[0]
        CheeseInfo.epid = info_episode["id"]
        CheeseInfo.avid = info_episode["aid"]
        CheeseInfo.cid = info_episode["cid"]

    def get_cheese_quality(self):
        url = API.Cheese.download_api(CheeseInfo.avid, CheeseInfo.epid, CheeseInfo.cid)
        
        cheese_request = requests.get(url, headers = get_header(CheeseInfo.url, cookie = Config.user_sessdata), proxies = get_proxy(), auth = get_auth())
        cheese_json = json.loads(cheese_request.text)
        
        if self.check_json(cheese_json): return

        json_data = cheese_json["data"]
        CheeseInfo.quality_id = json_data["accept_quality"]
        CheeseInfo.quality_desc = json_data["accept_description"]

    def parse_url(self, url):
        if "ep" in url:
            self.get_epid(url)
        elif "ss" in url:
            self.get_season_id(url)

        self.get_cheese_info()
        self.get_cheese_quality()

    def check_json(self, json):  
        if json["code"] != 0:
            if json["message"] == "请求错误":
                self.onError(403)
            else:
                self.onError(400)
        
        return True
