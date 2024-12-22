import re
import json
import requests

from utils.tool_v2 import RequestTool, UniversalTool
from utils.common.enums import StatusCode

class FestivalInfo:
    url: str = ""

class FestivalParser:
    def __init__(self, onError):
        self.onError = onError

    def get_aid(self, initial_state):
        # 其他类型的视频则提供 aid，取第 1 个即可
        aid = re.findall(r'"aid":([0-9]+)', initial_state)

        if not aid:
            raise Exception(StatusCode.URL.value)

        FestivalInfo.url = f"https://www.bilibili.com/video/{UniversalTool.aid_to_bvid(int(aid[0]))}"

    def get_bvid(self, url: str):
        bvid = re.findall(r"BV\w+", url)

        if not bvid:
            raise Exception(StatusCode.URL.value)

        FestivalInfo.url = f"https://www.bilibili.com/video/{bvid[0]}"

    def get_initial_state(self, url: str):
        # 活动页链接不会包含 BV 号，ep 号等关键信息，故采用网页解析方式获取视频数据

        req = requests.get(url, headers = RequestTool.get_headers(), proxies = RequestTool.get_proxies(), auth = RequestTool.get_auth())

        if "window.__initialState" in req.text:
            initial_state_info = re.findall(r"window.__initialState = (.*?);", req.text)

        if "window.__INITIAL_STATE__" in req.text:
            initial_state_info = re.findall(r"window.__INITIAL_STATE__=(.*?);", req.text)

        return initial_state_info[0]

    def get_real_url(self, initial_state):
        # 获取真实链接

        if "https://www.bilibili.com/bangumi/play/ss" in initial_state:
            # 直接查找跳转链接
            jump_url = re.findall(r"https://www.bilibili.com/bangumi/play/ss[0-9]+", initial_state)

            FestivalInfo.url = jump_url[0]

            return

        if "videoInfo" in initial_state:
            # 解析网页中的json信息
            info_json = json.loads(initial_state)

            # 找到当前视频的 bvid
            bvid = info_json["videoInfo"]["bvid"]

            FestivalInfo.url = f"https://www.bilibili.com/video/{bvid}"

            return

        if "aid" in initial_state:
            self.get_aid(initial_state)

    def parse_url(self, url: str):
        match UniversalTool.re_find_string(r"BV", url):
            case "BV":
                # 判断视频链接是否包含 BV 号
                self.get_bvid(url)

            case _:
                initial_state = self.get_initial_state(url)

                self.get_real_url(initial_state)
