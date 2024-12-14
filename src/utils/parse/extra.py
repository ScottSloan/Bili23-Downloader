import os
import json
import math
import datetime
import requests

from utils.config import Config
from utils.tool_v2 import RequestTool, UniversalTool

class ExtraInfo:
    get_danmaku: bool = False
    danmaku_type: int = 0

    get_subtitle: bool = False
    subtitle_type: int = 0

    get_cover: bool = False

    @staticmethod
    def clear_extra_info():
        ExtraInfo.get_danmaku = ExtraInfo.get_subtitle = ExtraInfo.get_cover = False
        ExtraInfo.danmaku_type = ExtraInfo.subtitle_type = 0

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
        def get_subtitle_json(subtitle_url: str):
            req = requests.get(subtitle_url, headers = RequestTool.get_headers(sessdata = Config.User.sessdata), proxies = RequestTool.get_proxies(), auth = RequestTool.get_auth())

            return json.loads(req.text)
        
        url = f"https://api.bilibili.com/x/player/wbi/v2?bvid={self.bvid}&cid={self.cid}&w_rid={Config.Auth.wbi_key}&wts={UniversalTool.get_timestamp()}"

        req = requests.get(url, headers = RequestTool.get_headers(sessdata = Config.User.sessdata), proxies = RequestTool.get_proxies(), auth = RequestTool.get_auth())
        resp = json.loads(req.text)

        subtitle_list = resp["data"]["subtitle"]["subtitles"]

        for entry in subtitle_list:
            lan = entry["lan"]
            lan_doc = entry["lan_doc"]
            subtitle_url = "https:" + entry["subtitle_url"]

            self.parse_subtitle_json(get_subtitle_json(subtitle_url), lan)

    def parse_subtitle_json(self, json: dict, lan: str):
        def _format_timestamp(_from: float, _to: float):
            def _get_timestamp(t: float):
                ms = int((t - int(t)) * 1000)

                _t = str(datetime.timedelta(seconds = int(t))).split('.')[0]

                return f"{_t},{ms:03d}"

            return f"{_get_timestamp(_from)} --> {_get_timestamp(_to)}"

        _temp = ""

        for index, entry in enumerate(json["body"]):
            id = index + 1
            timestamp = _format_timestamp(entry["from"], entry["to"])
            content = entry["content"]

            _temp += f"{id}\n{timestamp}\n{content}\n\n"

        path = os.path.join(Config.Download.path, f"{self.title}_{lan}.srt")
        
        with open(path, "w", encoding = "utf-8") as f:
            f.write(_temp)
