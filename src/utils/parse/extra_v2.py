import os
import math
import json
from utils.config import Config

from utils.common.data_type import DownloadTaskInfo, Callback
from utils.common.enums import DanmakuType, SubtitleType, SubtitleLanOption, StatusCode
from utils.common.request import RequestUtils
from utils.common.file_name_v2 import FileNameFormatter
from utils.common.formatter import FormatUtils
from utils.common.exception import GlobalException

from utils.module.cover import CoverUtils

from utils.auth.wbi import WbiUtils

class ExtraParser:
    class Danmaku:
        @classmethod
        def download(cls, task_info: DownloadTaskInfo):
            base_file_name = FileNameFormatter.format_file_name(task_info)

            match DanmakuType(task_info.extra_option.get("danmaku_file_type")):
                case DanmakuType.XML:
                    cls.get_xml_file(task_info, base_file_name)

                case DanmakuType.Protobuf:
                    cls.get_protobuf_file(task_info, base_file_name)

        @staticmethod
        def get_xml_file(task_info: DownloadTaskInfo, base_file_name: str):
            url = f"https://comment.bilibili.com/{task_info.cid}.xml"

            req = ExtraParser.Utils.request_get(url)

            ExtraParser.Utils.save_to_file(f"{base_file_name}.xml", req.text, task_info, "w")

        @staticmethod
        def get_protobuf_file(task_info: DownloadTaskInfo, base_file_name: str):
            def get_file_name():
                if p_count > 1:
                    return f"{base_file_name}_part{index}.protobuf"
                else:
                    return f"{base_file_name}.protobuf"

            def get_file():
                url = f"https://api.bilibili.com/x/v2/dm/web/seg.so?type=1&oid={task_info.cid}&segment_index={index}"

                req = ExtraParser.Utils.request_get(url)

                file_name = get_file_name()

                ExtraParser.Utils.save_to_file(file_name, req.content, task_info, "wb")

            if task_info.duration:
                p_count = math.ceil(task_info.duration / 360)

                for index in range(1, p_count + 1):
                    get_file()

    class Subtitle:
        @classmethod
        def download(cls, task_info: DownloadTaskInfo):
            info = cls.query_all_subtitles(task_info)

            subtitle_list = info["data"]["subtitle"]["subtitles"]

            for entry in subtitle_list:
                lan = entry["lan"]
                            
                match SubtitleLanOption(Config.Basic.subtitle_lan_option):
                    case SubtitleLanOption.All_Subtitles:
                        if lan in ["ai-zh", "ai-en"]:
                            continue

                    case SubtitleLanOption.Custom:
                        if lan not in Config.Basic.subtitle_lan_custom_type:
                            continue

                subtitle_url = "https:" + entry["subtitle_url"]

                cls.convert_subtitle(task_info, subtitle_url, lan)
        
        @staticmethod
        def query_all_subtitles(task_info: DownloadTaskInfo):
            params = {
                "bvid": task_info.bvid,
                "cid": task_info.cid
            }

            url = f"https://api.bilibili.com/x/player/wbi/v2?{WbiUtils.encWbi(params)}"

            req = ExtraParser.Utils.request_get(url)

            return json.loads(req.text)

        @staticmethod
        def get_subtitle_json(url: str):
            req = ExtraParser.Utils.request_get(url)

            return json.loads(req.text)
        
        @classmethod
        def convert_subtitle(cls, task_info: DownloadTaskInfo, subtitle_url: str, lan: str):
            base_file_name = FileNameFormatter.format_file_name(task_info)

            subtitle_json = cls.get_subtitle_json(subtitle_url)

            match SubtitleType(task_info.extra_option.get("subtitle_file_type")):
                case SubtitleType.SRT:
                    cls.convert_to_srt(task_info, subtitle_json, lan, base_file_name)

                case SubtitleType.TXT:
                    cls.convert_to_txt(task_info, subtitle_json, lan, base_file_name)

                case SubtitleType.LRC:
                    cls.convert_to_lrc(task_info, subtitle_json, lan, base_file_name)

                case SubtitleType.JSON:
                    cls.convert_to_json(task_info, subtitle_json, lan, base_file_name)
        
        @staticmethod
        def convert_to_srt(task_info: DownloadTaskInfo, subtitle_json: dict, lan: str, base_file_name: str):
            contents = ""

            for index, entry in enumerate(subtitle_json["body"]):
                id = index + 1
                timestamp = FormatUtils.format_srt_line(entry["from"], entry["to"])
                content = entry["content"]

                contents += f"{id}\n{timestamp}\n{content}\n\n"

            ExtraParser.Utils.save_to_file(f"{base_file_name}_{lan}.srt", contents, task_info, "w")

        @staticmethod
        def convert_to_txt(task_info: DownloadTaskInfo, subtitle_json: dict, lan: str, base_file_name: str):
            contents = ""

            for entry in subtitle_json["body"]:
                content = entry["content"]

                contents += f"{content}\n"

            ExtraParser.Utils.save_to_file(f"{base_file_name}_{lan}.txt", contents, task_info, "w")

        @staticmethod
        def convert_to_lrc(task_info: DownloadTaskInfo, subtitle_json: dict, lan: str, base_file_name: str):
            contents = ""

            for entry in subtitle_json["body"]:
                timestamp = FormatUtils.format_lrc_line(entry["from"])
                content = entry["content"]

                contents += f"[{timestamp}]{content}\n"

            ExtraParser.Utils.save_to_file(f"{base_file_name}_{lan}.lrc", contents, task_info, "w")

        @staticmethod
        def convert_to_json(task_info: DownloadTaskInfo, subtitle_json: dict, lan: str, base_file_name: str):
            contents = json.dumps(subtitle_json, ensure_ascii = False, indent = 4)

            ExtraParser.Utils.save_to_file(f"{base_file_name}_{lan}.json", contents, task_info, "w")

    class Cover:
        @classmethod
        def download(cls, task_info: DownloadTaskInfo):
            base_file_name = FileNameFormatter.format_file_name(task_info)

            cover_type = CoverUtils.get_cover_type()

            contents = CoverUtils.download_cover(task_info.cover_url)

            ExtraParser.Utils.save_to_file(f"{base_file_name}{cover_type}", contents, task_info, "wb")

    class Utils:
        @staticmethod
        def download(task_info: DownloadTaskInfo, callback: Callback):
            try:
                if task_info.extra_option.get("download_danmaku_file"):
                    ExtraParser.Danmaku.download(task_info)

                if task_info.extra_option.get("download_subtitle_file"):
                    ExtraParser.Subtitle.download(task_info)

                if task_info.extra_option.get("download_cover_file"):
                    ExtraParser.Cover.download(task_info)

                task_info.total_downloaded_size = task_info.total_file_size

                callback.onSuccess()

            except Exception as e:
                raise GlobalException(code = StatusCode.DownloadError.value, callback = callback.onError) from e

        @staticmethod
        def request_get(url: str):
            return RequestUtils.request_get(url, headers = RequestUtils.get_headers(sessdata = Config.User.SESSDATA))

        @staticmethod
        def save_to_file(file_name: str, contents: str, task_info: DownloadTaskInfo, mode: str):
            download_path = FileNameFormatter.get_download_path(task_info)

            file_path = os.path.join(download_path, file_name)

            encoding = "utf-8" if mode == "w" else None

            with open(file_path, mode, encoding = encoding) as f:
                f.write(contents)