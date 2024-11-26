import os
import requests

from utils.config import Config
from utils.tool_v2 import RequestTool

class ExtraInfo:
    get_danmaku: bool = False
    danmaku_type: int = 0

    get_cover: bool = False

    @staticmethod
    def clear_extra_info():
        ExtraInfo.get_danmaku = ExtraInfo.get_cover = False
        ExtraInfo.danmaku_type = 0

class ExtraParser:
    def __init__(self, title: str, cid: int, duration: int):
        self.title, self.cid, self.duration = title, cid, duration

    def get_danmaku(self):
        # 下载弹幕文件
        match ExtraInfo.danmaku_type:
            case Config.Type.DANMAKU_TYPE_XML:
                self.get_danmaku_xml()

            case Config.Type.DANMAKU_TYPE_PROTOBUF:
                self.get_danmaku_protobuf()

    def get_danmaku_xml(self):
        # 下载 xml 格式弹幕文件
        url = f"https://comment.bilibili.com/{self.cid}.xml"

        req = requests.get(url, headers = RequestTool.get_headers(sessdata = Config.User.sessdata), proxies = RequestTool.get_proxies(), auth = RequestTool.get_auth())

        path = os.path.join(Config.Download.path, f"{self.title}.xml")

        with open (path, "wb") as f:
            f.write(req.content)

    def get_danmaku_protobuf(self):
        # 下载 protobuf 格式弹幕文件
        url = f"https://api.bilibili.com/x/v2/dm/web/seg.so?type=1&oid={self.cid}&segment_index=1"

        req = requests.get(url, headers = RequestTool.get_headers(sessdata = Config.User.sessdata), proxies = RequestTool.get_proxies(), auth = RequestTool.get_auth())

        path = os.path.join(Config.Download.path, f"{self.title}.protobuf")

        with open(path, "wb") as f:
            f.write(req.content)
