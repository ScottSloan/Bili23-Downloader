import os
import json
import math
import datetime
import requests

from utils.config import Config
from utils.tool_v2 import RequestTool
from utils.auth.wbi import WbiUtils
from utils.common.enums import DanmakuType, SubtitleType

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
        match DanmakuType(ExtraInfo.danmaku_type):
            case DanmakuType.XML:
                self.get_danmaku_xml()

            case DanmakuType.Protobuf:
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
        
        def _to_srt(subtitle_json: dict, lan: str):
            def _format_timestamp(_from: float, _to: float):
                def _get_timestamp(t: float):
                    ms = int((t - int(t)) * 1000)

                    _t = str(datetime.timedelta(seconds = int(t))).split('.')[0]

                    return f"{_t},{ms:03d}"

                return f"{_get_timestamp(_from)} --> {_get_timestamp(_to)}"

            _temp = ""

            for index, entry in enumerate(subtitle_json["body"]):
                id = index + 1
                timestamp = _format_timestamp(entry["from"], entry["to"])
                content = entry["content"]

                _temp += f"{id}\n{timestamp}\n{content}\n\n"

            _save(_temp, f"{self.title}_{lan}.srt")

        def _to_txt(subtitle_json: dict, lan: str):
            _temp = ""

            for entry in subtitle_json["body"]:
                content = entry["content"]

                _temp += f"{content}\n"

            _save(_temp, f"{self.title}_{lan}.txt")
        
        def _to_json(subtitle_json: dict, lan: str):
            _temp = json.dumps(subtitle_json, ensure_ascii = False, indent = 4)

            _save(_temp, f"{self.title}_{lan}.json")

        def _save(_temp: str, file_name: str):
            path = os.path.join(Config.Download.path, file_name)

            with open(path, "w", encoding = "utf-8") as f:
                f.write(_temp)

        params = {
            "bvid": self.bvid,
            "cid": self.cid
        }

        url = f"https://api.bilibili.com/x/player/wbi/v2?{WbiUtils.encWbi(params)}"

        req = requests.get(url, headers = RequestTool.get_headers(sessdata = Config.User.sessdata), proxies = RequestTool.get_proxies(), auth = RequestTool.get_auth())
        resp = json.loads(req.text)

        subtitle_list = resp["data"]["subtitle"]["subtitles"]

        for entry in subtitle_list:
            lan = entry["lan"]
            # lan_doc = entry["lan_doc"]
            subtitle_url = "https:" + entry["subtitle_url"]

            subtitle_json = get_subtitle_json(subtitle_url)

            match SubtitleType(ExtraInfo.subtitle_type):
                case SubtitleType.SRT:
                    _to_srt(subtitle_json, lan)

                case SubtitleType.TXT:
                    _to_txt(subtitle_json, lan)

                case SubtitleType.JSON:
                    _to_json(subtitle_json, lan)