import os
import json
import math
import requests

from utils.config import Config
from utils.tool_v2 import RequestTool, UniversalTool

class ExtraInfo:
    get_danmaku: bool = False
    danmaku_type: int = 0

    get_cover: bool = False

    @staticmethod
    def clear_extra_info():
        ExtraInfo.get_danmaku = ExtraInfo.get_cover = False
        ExtraInfo.danmaku_type = 0

class ExtraParser:
    def __init__(self, title: str, bvid: str, cid: int, duration: int):
        self.title, self.bvid, self.cid, self.duration = title, bvid, cid, duration

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
        def _get_protobuf(index: int, _package_count: int):
            def _get_file_name(index: int, _package_count: int):
                if _package_count == 1:
                    return f"{self.title}.protobuf"
                else:
                    return f"{self.title}_part{index}.protobuf"
            
            # 下载 protobuf 格式弹幕文件
            url = f"https://api.bilibili.com/x/v2/dm/web/seg.so?type=1&oid={self.cid}&segment_index={index}"

            req = requests.get(url, headers = RequestTool.get_headers(sessdata = Config.User.sessdata), proxies = RequestTool.get_proxies(), auth = RequestTool.get_auth())

            path = os.path.join(Config.Download.path, _get_file_name(index, _package_count))

            with open(path, "wb") as f:
                f.write(req.content)

        # protobuf 每 6min 分一包，向上取整下载全部分包
        _package_count = math.ceil(self.duration / 360)

        for i in range(_package_count):
            _get_protobuf(i + 1)

    def get_subtitle(self):
        url = f"https://api.bilibili.com/x/player/wbi/v2?bvid={self.bvid}&cid={self.cid}&w_rid={Config.Auth.wbi_key}&wts={UniversalTool.get_timestamp()}"

        req = requests.get(url, headers = RequestTool.get_headers(sessdata = Config.User.sessdata), proxies = RequestTool.get_proxies(), auth = RequestTool.get_auth())

        resp = json.loads(req.text)

        subtitle_list = resp["data"]["subtitle"]["subtitles"]

        for entry in subtitle_list:
            lan = entry["lan"]
            lan_doc = entry["lan_doc"]
            subtitle_url = entry["subtitle_url"]
