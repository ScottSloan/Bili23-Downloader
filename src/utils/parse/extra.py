import os
import json
import math
import datetime

from utils.config import Config
from utils.tool_v2 import RequestTool, FormatTool
from utils.auth.wbi import WbiUtils
from utils.common.enums import DanmakuType, SubtitleType
from utils.common.data_type import DownloadTaskInfo

class ExtraInfo:
    download_danmaku_file: bool = False
    danmaku_file_type: int = 0

    download_subtitle_file: bool = False
    subtitle_file_type: int = 0

    download_cover_file: bool = False

    @staticmethod
    def clear_extra_info():
        ExtraInfo.download_danmaku_file = False
        ExtraInfo.download_subtitle_file = False
        ExtraInfo.download_cover_file = False

        ExtraInfo.danmaku_file_type = 0
        ExtraInfo.subtitle_file_type = 0

    @staticmethod
    def to_dict():
        return {
            "download_danmaku_file": ExtraInfo.download_danmaku_file,
            "danmaku_file_type": ExtraInfo.danmaku_file_type,
            "download_subtitle_file": ExtraInfo.download_subtitle_file,
            "subtitle_file_type": ExtraInfo.subtitle_file_type,
            "download_cover_file": ExtraInfo.download_cover_file
        }

class ExtraParser:
    def __init__(self):
        pass

    def set_task_info(self, task_info: DownloadTaskInfo):
        self.task_info = task_info
        self.file_name = FormatTool.format_title_template(Config.Advanced.file_name_template, self.task_info)

        self.danmaku_file_type = task_info.extra_option.get("danmaku_file_type")
        self.subtitle_file_type = task_info.extra_option.get("subtitle_file_type")

    def download_danmaku_file(self):
        # 下载弹幕文件
        match DanmakuType(self.danmaku_file_type):
            case DanmakuType.XML:
                self.convert_danmaku_to_xml()

            case DanmakuType.Protobuf:
                self.convert_danmaku_to_protobuf()

    def convert_danmaku_to_xml(self):
        # 下载 xml 格式弹幕文件
        url = f"https://comment.bilibili.com/{self.task_info.cid}.xml"

        req = RequestTool.request_get(url, headers = RequestTool.get_headers(sessdata = Config.User.SESSDATA))

        file_name = f"{self.file_name}.xml"
        self.write_to_file(file_name, req.content, mode = "wb")

    def convert_danmaku_to_protobuf(self):
        def get_protobuf(index: int, _package_count: int):
            def get_file_name(index: int, _package_count: int):
                if _package_count == 1:
                    return f"{self.file_name}.protobuf"
                else:
                    return f"{self.file_name}_part{index}.protobuf"
            
            # 下载 protobuf 格式弹幕文件
            url = f"https://api.bilibili.com/x/v2/dm/web/seg.so?type=1&oid={self.task_info.cid}&segment_index={index}"

            req = RequestTool.request_get(url, headers = RequestTool.get_headers(sessdata = Config.User.SESSDATA))

            file_name = get_file_name(index, _package_count)
            self.write_to_file(file_name, req.content, mode = "wb")

        # protobuf 每 6min 分一包，向上取整下载全部分包
        _package_count = math.ceil(self.task_info.duration / 360)

        for i in range(_package_count):
            get_protobuf(i + 1)

    def download_subtitle_file(self):
        def get_subtitle_json(subtitle_url: str):
            req = RequestTool.request_get(subtitle_url, headers = RequestTool.get_headers(sessdata = Config.User.SESSDATA))

            return json.loads(req.text)

        params = {
            "bvid": self.task_info.bvid,
            "cid": self.task_info.cid
        }

        url = f"https://api.bilibili.com/x/player/wbi/v2?{WbiUtils.encWbi(params)}"

        req = RequestTool.request_get(url, headers = RequestTool.get_headers(sessdata = Config.User.SESSDATA))
        resp = json.loads(req.text)

        subtitle_list = resp["data"]["subtitle"]["subtitles"]

        for entry in subtitle_list:
            lan = entry["lan"]
            # lan_doc = entry["lan_doc"]
            subtitle_url = "https:" + entry["subtitle_url"]

            subtitle_json = get_subtitle_json(subtitle_url)

            match SubtitleType(self.subtitle_file_type):
                case SubtitleType.SRT:
                    self.convert_subtitle_to_srt(subtitle_json, lan)

                case SubtitleType.TXT:
                    self.convert_subtitle_to_txt(subtitle_json, lan)

                case SubtitleType.LRC:
                    self.convert_subtitle_to_lrc(subtitle_json, lan)

                case SubtitleType.JSON:
                    self.convert_subtitle_to_json(subtitle_json, lan)

    def convert_subtitle_to_srt(self, subtitle_json: dict, lan: str):
        def format_timestamp(_from: float, _to: float):
            def get_timestamp(t: float):
                ms = int((t - int(t)) * 1000)

                t = str(datetime.timedelta(seconds = int(t))).split('.')[0]

                return f"{t},{ms:03d}"

            return f"{get_timestamp(_from)} --> {get_timestamp(_to)}"

        contents = ""

        for index, entry in enumerate(subtitle_json["body"]):
            id = index + 1
            timestamp = format_timestamp(entry["from"], entry["to"])
            content = entry["content"]

            contents += f"{id}\n{timestamp}\n{content}\n\n"

        file_name = f"{self.file_name}_{lan}.srt"
        self.write_to_file(file_name, contents)

    def convert_subtitle_to_txt(self, subtitle_json: dict, lan: str):
        contents = ""

        for entry in subtitle_json["body"]:
            content = entry["content"]

            contents += f"{content}\n"

        file_name = f"{self.file_name}_{lan}.txt"
        self.write_to_file(file_name, contents)

    def convert_subtitle_to_lrc(self, subtitle_json: dict, lan: str):
        def _format_timestamp(from_time: float):
            min = int(from_time // 60)
            sec = from_time % 60

            return f"{min:02}:{sec:04.1f}"

        contents = ""

        for entry in subtitle_json["body"]:
            timestamp = _format_timestamp(entry["from"])
            content = entry["content"]

            contents += f"[{timestamp}]{content}\n"

        file_name = f"{self.file_name}_{lan}.lrc"
        self.write_to_file(file_name, contents)

    def convert_subtitle_to_json(self, subtitle_json: dict, lan: str):
        contents = json.dumps(subtitle_json, ensure_ascii = False, indent = 4)

        file_name = f"{self.file_name}_{lan}.json"
        self.write_to_file(file_name, contents)

    def download_cover_file(self):
        req = RequestTool.request_get(self.task_info.cover_url)

        file_name = f"{self.task_info.title}.jpg"
        self.write_to_file(file_name, req.content, mode = "wb")

    def write_to_file(self, file_name: str, contents: str, mode: str = "w"):
        path = os.path.join(Config.Download.path, file_name)

        if mode == "w":
            encoding = "utf-8"
        else:
            encoding = None

        with open(path, mode, encoding = encoding) as f:
            f.write(contents)