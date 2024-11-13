import os
import requests
from utils.config import Config
from utils.tools import get_header, get_proxy, get_auth

class ExtraParser:
    def __init__(self, title: str, cid: int):
        self.title, self.cid = title, cid

    def get_danmaku(self):
        # 下载弹幕文件
        match Config.Extra.danmaku_format:
            case Config.Type.DANMAKU_TYPE_XML:
                self.get_danmaku_xml()

            case Config.Type.DANMAKU_TYPE_PROTOBUF:
                self.get_danmaku_protobuf()

    def get_danmaku_xml(self):
        # 下载 xml 格式弹幕文件
        url = f"https://comment.bilibili.com/{self.cid}.xml"

        req = requests.get(url, headers = get_header(), proxies = get_proxy(), auth = get_auth())

        path = os.path.join(Config.Download.path, f"{self.title}.xml")

        with open (path, "wb") as f:
            f.write(req.content)

    def get_danmaku_protobuf(self):
        # 下载 protobuf 格式弹幕文件
        pass

    def get_cover(self):
        # 下载视频封面
        pass