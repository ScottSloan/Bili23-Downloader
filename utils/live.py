import re
import json
import requests

from utils.config import Config
from utils.tools import *

class LiveInfo:
    id = room_id = live_status = 0

    title = playurl = ""
    
class LiveParser:
    def info_api(self):
        return "https://api.live.bilibili.com/xlive/web-room/v1/index/getRoomBaseInfo?room_ids={}&req_biz=web_room_componet".format(LiveInfo.id)

    def playurl_api(self):
        return "https://api.live.bilibili.com/xlive/web-room/v2/index/getRoomPlayInfo?room_id={}&no_playurl=0&mask=1&qn=0&platform=web&protocol=0,1&format=0,1,2&codec=0,1".format(LiveInfo.room_id)
    
    def get_id(self, url: str):
        LiveInfo.id = re.findall(r"com/[0-9]*", url)[0][4:]

    def get_live_info(self):
        live_req = requests.get(self.info_api(), headers = get_header(), proxies = get_proxy())
        live_json = json.loads(live_req.text)

        live_data = live_json["data"]["by_room_ids"]

        LiveInfo.room_id = list(live_data.keys())[0]
        LiveInfo.title = live_data[str(LiveInfo.room_id)]["title"]
        LiveInfo.live_status = live_data[str(LiveInfo.room_id)]["live_status"]

    def get_live_playurl(self):
        live_req = requests.get(self.playurl_api(), headers = get_header(cookie = Config.cookie_sessdata), proxies = get_proxy())
        live_json = json.loads(live_req.text)

        codec = live_json["data"]["playurl_info"]["playurl"]["stream"][1]["format"][1]["codec"][0]
        base_url = codec["base_url"]
        host = codec["url_info"][0]["host"]
        LiveInfo.playurl = host + base_url

    def parse_url(self, url: str):
        self.get_id(url)

        self.get_live_info()
        self.get_live_playurl()
