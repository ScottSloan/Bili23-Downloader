import re
import json
import requests
from typing import List, Dict

from utils.tool_v2 import RequestTool, UniversalTool
from utils.config import Config
from utils.common.exception import ErrorUtils, StatusCode, GlobalException
from utils.common.map import live_status_map
from utils.parse.episode import EpisodeInfo, live_episode_parser

class LiveInfo:
    title: str = ""

    room_id: int = 0
    short_id: int = 0

    status: int = 0
    status_str: str = ""

    m3u8_link: str = ""

    live_quality_id_list: List = []
    live_quality_desc_list: List = []

class LiveParser:
    def __init__(self, callback):
        self.callback = callback

    def get_short_id(self, url: str):
        short_id = re.findall(r"live.bilibili.com/([0-9]+)", url)

        if short_id:
            LiveInfo.short_id = short_id[0]

    def get_live_room_info(self):
        # 获取直播间信息
        url = f"https://api.live.bilibili.com/room/v1/Room/get_info?room_id={LiveInfo.short_id}"

        req = requests.get(url, headers = RequestTool.get_headers(sessdata = Config.User.sessdata), proxies = RequestTool.get_proxies(), auth = RequestTool.get_auth())
        resp = json.loads(req.text)

        self.check_json(resp)

        info = resp["data"]

        LiveInfo.title = UniversalTool.get_legal_name(info["title"])
        LiveInfo.room_id = info["room_id"]

        LiveInfo.status = info["live_status"]
        LiveInfo.status_str = live_status_map[LiveInfo.status]

        EpisodeInfo.clear_episode_data("直播")

        live_episode_parser(LiveInfo.title, LiveInfo.status_str)

    def get_live_available_media_info(self):
        url = f"https://api.live.bilibili.com/room/v1/Room/playUrl?cid={LiveInfo.room_id}&platform=h5"

        req = requests.get(url, headers = RequestTool.get_headers(sessdata = Config.User.sessdata), proxies = RequestTool.get_proxies(), auth = RequestTool.get_auth())
        resp = json.loads(req.text)

        self.check_json(resp)

        info = resp["data"]

        quality_description = info["quality_description"]

        LiveInfo.live_quality_id_list = [entry["qn"] for entry in quality_description]
        LiveInfo.live_quality_desc_list = [entry["desc"] for entry in quality_description]

    def get_live_stream(self, qn: int):
        url = f"https://api.live.bilibili.com/room/v1/Room/playUrl?cid={LiveInfo.room_id}&platform=h5&qn={qn}"

        req = requests.get(url, headers = RequestTool.get_headers(sessdata = Config.User.sessdata), proxies = RequestTool.get_proxies(), auth = RequestTool.get_auth())
        resp = json.loads(req.text)

        self.check_json(resp)

        info = resp["data"]

        LiveInfo.m3u8_link = info["durl"][0]["url"]

    def parse_url(self, url: str):
        def worker():
            # 清除当前直播信息
            self.clear_live_info()

            # 获取直播间短号
            self.get_short_id(url)

            self.get_live_room_info()

            self.get_live_available_media_info()
        
        try:
            worker()

        except Exception as e:
            raise GlobalException(e, callback = self.callback)

    def check_json(self, json: Dict):
        # 检查接口返回状态码
        status_code = json["code"]
        error = ErrorUtils()

        if status_code != StatusCode.CODE_0:
            raise Exception("{} ({})".format(error.getStatusInfo(status_code), status_code))

    def clear_live_info(self):
        LiveInfo.title = ""

        LiveInfo.room_id = LiveInfo.short_id = 0

        LiveInfo.live_quality_id_list.clear()
        LiveInfo.live_quality_desc_list.clear()
