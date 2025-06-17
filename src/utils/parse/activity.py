import re
import json

from utils.common.enums import StatusCode
from utils.common.exception import GlobalException
from utils.common.data_type import ParseCallback
from utils.common.request import RequestUtils
from utils.common.re_utils import REUtils

from utils.parse.parser import Parser

class ActivityInfo:
    url: str = ""

class ActivityParser(Parser):
    def __init__(self, callback: ParseCallback):
        super().__init__()
        
        self.callback = callback

    def get_aid(self, initial_state: str):
        aid = self.re_find_str(r'"aid":([0-9]+)', initial_state)

        ActivityInfo.url = f"https://www.bilibili.com/video/{self.aid_to_bvid(int(aid[0]))}"

    def get_bvid(self, url: str):
        bvid = self.re_find_str(r"BV\w+", url)

        ActivityInfo.url = f"https://www.bilibili.com/video/{bvid[0]}"

    def get_initial_state(self, url: str):
        # 活动页链接不会包含 BV 号，ep 号等关键信息，故采用网页解析方式获取视频数据

        req = RequestUtils.request_get(url, headers = RequestUtils.get_headers())

        if "window.__initialState" in req.text:
            initial_state_info = re.findall(r"window.__initialState = (.*?);", req.text)

        elif "window.__INITIAL_STATE__" in req.text:
            initial_state_info = re.findall(r"window.__INITIAL_STATE__=(.*?);", req.text)

        return initial_state_info[0]

    def get_real_url(self, initial_state):
        if "https://www.bilibili.com/bangumi/play/ss" in initial_state:
            # 直接查找跳转链接
            jump_url = re.findall(r"https://www.bilibili.com/bangumi/play/ss[0-9]+", initial_state)

            ActivityInfo.url = jump_url[0]

        elif "videoInfo" in initial_state:
            # 解析网页中的json信息
            info_json = json.loads(initial_state)

            # 找到当前视频的 bvid
            bvid = info_json["videoInfo"]["bvid"]

            ActivityInfo.url = f"https://www.bilibili.com/video/{bvid}"

        elif "aid" in initial_state:
            self.get_aid(initial_state)

    def parse_url(self, url: str):
        def worker():
            match REUtils.find_string(r"BV", url):
                case "BV":
                    # 判断视频链接是否包含 BV 号
                    self.get_bvid(url)

                case _:
                    initial_state = self.get_initial_state(url)

                    self.get_real_url(initial_state)

            raise GlobalException(code = StatusCode.Redirect.value, callback = self.callback.onBangumi, args = (ActivityInfo.url, ))
        
        try:
            return worker()

        except Exception as e:
            raise GlobalException(callback = self.callback.onError) from e
