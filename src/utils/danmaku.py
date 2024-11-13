import os
import requests
from utils.config import Config
from utils.tools import get_header, get_proxy, get_auth

class DanmakuParser:
    def __init__(self):
        pass

    def get_danmaku(self, title: str, cid: int):
        url = f"https://comment.bilibili.com/{cid}.xml"

        req = requests.get(url, headers = get_header(), proxies = get_proxy(), auth = get_auth())

        path = os.path.join(Config.Download.path, f"{title}.xml")

        with open (path, "wb") as f:
            f.write(req.content)