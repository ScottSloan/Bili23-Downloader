import requests

from .tools import *

class ActivityInfo:
    new_url = None

class ActivityParser:
    def __init__(self, onError):
        self.onError = onError

    def get_aid(self, url):
        req = requests.get(url, headers = get_header(), proxies = get_proxy(), auth = get_auth())
        
        if "videoID" in req.text:
            self.get_epid(req.text)
            return

        aid = re.findall(r'"aid":([0-9]+)', req.text)

        if not aid: self.onError(101)

        ActivityInfo.new_url = f"https://www.bilibili.com/video/{convert_to_bvid(int(aid[0]))}"

    def get_epid(self, page: str):
        epid = re.findall(r"\"videoID\":\"([0-9]+)\"", page.replace("\\", ""), re.S)

        if not epid: self.onError(101)

        ActivityInfo.new_url = f"https://www.bilibili.com/bangumi/play/ep{epid[0]}"

    def parse_url(self, url: str):
        if "blackboard" in url:
            self.get_aid(url)
