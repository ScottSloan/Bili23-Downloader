import re
import json
import requests

from .config import Config
from .tools import *
from .api import API

class LiveInfo:
    id = room_id = live_status = 0

    title = playurl = ""

class LiveParser:
    def __init__(self, onError):
        self.onError = onError
    
    def get_id(self, url):
        try:
            LiveInfo.id = re.findall(r"com/([0-9]*)", url)[0]
        except:
            self.onError(400)
            return

    def get_live_info(self):
        url = API.Live.info_api(LiveInfo.id)

        live_req = requests.get(url, headers = get_header(), proxies = get_proxy(), auth = get_auth())
        live_json = json.loads(live_req.text)

        if self.check_json(live_json): return

        live_data = live_json["data"]["by_room_ids"]

        LiveInfo.room_id = list(live_data.keys())[0]
        LiveInfo.title = live_data[str(LiveInfo.room_id)]["title"]
        LiveInfo.live_status = live_data[str(LiveInfo.room_id)]["live_status"]

    def get_live_playurl(self):
        url = API.Live.playurl_api(LiveInfo.room_id)

        live_req = requests.get(url, headers = get_header(cookie = Config.user_sessdata), proxies = get_proxy(), auth = get_auth())
        live_json = json.loads(live_req.text)

        if self.check_json(live_json, flag = True): return

        LiveInfo.playurl = live_json["data"]["durl"][0]["url"]

    def parse_url(self, url):
        self.get_id(url)

        self.get_live_info()
        self.get_live_playurl()
    
    def  check_json(self, json, flag):
        if json["code"] != 0 and flag:
            self.onError(404)
        else:
            self.onError(400)
        
        return True
