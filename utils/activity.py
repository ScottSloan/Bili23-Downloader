import requests

from .tools import *

class ActivityInfo:
    new_url = None

class ActivityParser:
    def __init__(self, onError):
        self.onError = onError

    def get_aid(self, initial_state):
        # 其他类型的视频则提供 aid，取第 1 个即可
        aid = re.findall(r'"aid":([0-9]+)', initial_state)

        if not aid: self.onError(100)

        ActivityInfo.new_url = f"https://www.bilibili.com/video/{convert_to_bvid(int(aid[0]))}"

    def get_initial_state(self, url):
        # 活动页链接不会包含 BV 号，ep 号等关键信息，故采用网页解析方式获取视频数据

        req = requests.get(url, headers = get_header(), proxies = get_proxy(), auth = get_auth())

        initial_state = re.findall(r"window.__initialState = (.*?);", req.text)

        if not initial_state: self.onError(100)

        return initial_state[0]

    def get_jump_url(self, initial_state):
        # 剧集类视频的活动页都有一个跳转链接（形如 https://www.bilibili.com/bangumi/play/ssxxxxxx，给的是season_id）

        jump_url = re.findall(r"https://www.bilibili.com/bangumi/play/ss[0-9]+", initial_state)

        if jump_url:
            ActivityInfo.new_url = jump_url[0]
        else:
            self.get_aid(initial_state)

    def parse_url(self, url: str):
        initial_state = self.get_initial_state(url)

        self.get_jump_url(initial_state)