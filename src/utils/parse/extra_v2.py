import os
import math
import json
from io import BytesIO
from typing import List
from google.protobuf import json_format
import utils.module.danmaku.dm_pb2 as dm_pb2

from utils.config import Config

from utils.common.data_type import DownloadTaskInfo, Callback, ASSStyle
from utils.common.enums import DanmakuType, SubtitleType, SubtitleLanOption, StatusCode
from utils.common.request import RequestUtils
from utils.common.file_name_v2 import FileNameFormatter
from utils.common.formatter import FormatUtils
from utils.common.exception import GlobalException

from utils.parse.preview import Preview
from utils.parse.download import DownloadParser

from utils.module.cover import Cover
from utils.module.danmaku.ass_file import ASS
from utils.module.danmaku.danmaku import Danmaku
from utils.module.danmaku.xml_file import XML

from utils.auth.wbi import WbiUtils

class ExtraParser:
    class Danmaku:
        @classmethod
        def download(cls, task_info: DownloadTaskInfo):
            base_file_name = FileNameFormatter.format_file_basename(task_info)

            io_buffer = cls.get_all_protobuf_contents(task_info)

            match DanmakuType(task_info.extra_option.get("danmaku_file_type")):
                case DanmakuType.XML:
                    cls.get_xml_file(io_buffer, task_info, base_file_name)

                case DanmakuType.Protobuf:
                    cls.get_protobuf_file(io_buffer, task_info, base_file_name)

                case DanmakuType.JSON:
                    cls.get_json_file(io_buffer, task_info, base_file_name)

                case DanmakuType.ASS:
                    cls.get_ass_file(io_buffer, task_info, base_file_name)

        @classmethod
        def get_xml_file(cls, io_buffer: List[BytesIO], task_info: DownloadTaskInfo, base_file_name: str):
            protobuf_dict = cls.get_protobuf_entry_list(io_buffer)

            contents = XML.make(protobuf_dict, task_info.cid)
            
            ExtraParser.Utils.save_to_file(f"{base_file_name}.xml", contents, task_info, "w")

        @classmethod
        def get_protobuf_file(cls, io_buffer: List[BytesIO], task_info: DownloadTaskInfo, base_file_name: str):
            def get_file_name():
                if len(io_buffer) > 1:
                    return f"{base_file_name}_part{index + 1}.protobuf"
                else:
                    return f"{base_file_name}.protobuf"

            for index, io in enumerate(io_buffer):
                ExtraParser.Utils.save_to_file(get_file_name, io.getvalue(), task_info, "wb")

        @classmethod
        def get_json_file(cls, io_buffer: List[BytesIO], task_info: DownloadTaskInfo, base_file_name: str):
            protobuf_dict = cls.get_protobuf_entry_list(io_buffer)

            contents = json.dumps({"comments": protobuf_dict}, ensure_ascii = False, indent = 4)

            ExtraParser.Utils.save_to_file(f"{base_file_name}.json", contents, task_info, "w")

        @classmethod
        def get_ass_file(cls, io_buffer: List[BytesIO], task_info: DownloadTaskInfo, base_file_name: str):
            protobuf_dict = cls.get_protobuf_entry_list(io_buffer)

            resolution = ExtraParser.Utils.get_video_resolution(task_info)

            danmaku = Danmaku(resolution.get("width"), resolution.get("height"))

            dialogue_list = danmaku.get_dialogue_list(protobuf_dict)
            style = danmaku.get_ass_style()

            contents = ASS.make(dialogue_list, style, resolution)

            ExtraParser.Utils.save_to_file(f"{base_file_name}.ass", contents, task_info, "w")
            
        @staticmethod
        def get_all_protobuf_contents(task_info: DownloadTaskInfo):
            def get_contents(cid: int, index: int):
                url = f"https://api.bilibili.com/x/v2/dm/web/seg.so?type=1&oid={cid}&segment_index={index}"

                return ExtraParser.Utils.request_get(url).content

            io_buffer = []

            if task_info.duration:
                p_count = math.ceil(task_info.duration / 360)

                for index in range(1, p_count + 1):
                    io_buffer.append(BytesIO(get_contents(task_info.cid, index)))

            return io_buffer

        @staticmethod
        def get_protobuf_entry_list(io_buffer: List[BytesIO]):
            temp = []

            seg = dm_pb2.DmSegMobileReply()

            for io in io_buffer:
                seg.ParseFromString(io.getvalue())

                temp_part = [json_format.MessageToDict(entry) for entry in seg.elems]

                part = [entry for entry in temp_part if "progress" in entry]

                temp.extend(part)

            temp.sort(key = lambda x: x["progress"])

            return temp

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
            base_file_name = FileNameFormatter.format_file_basename(task_info)

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

                case SubtitleType.ASS:
                    cls.convert_to_ass(task_info, subtitle_json, lan, base_file_name)
        
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

        @classmethod
        def convert_to_ass(cls, task_info: DownloadTaskInfo, subtitle_json: dict, lan: str, base_file_name: str):
            dialogue_list = [(FormatUtils.format_ass_timestamp(entry["from"]), FormatUtils.format_ass_timestamp(entry["to"]), entry["content"]) for entry in subtitle_json["body"]]
            style = cls.get_ass_style()

            contents = ASS.make(dialogue_list, style, ExtraParser.Utils.get_video_resolution(task_info))

            ExtraParser.Utils.save_to_file(f"{base_file_name}_{lan}.ass", contents, task_info, "w")

        @staticmethod
        def get_ass_style():
            subtitle = Config.Basic.ass_style.get("subtitle")

            ASSStyle.Name = "Default"
            ASSStyle.Fontname = subtitle.get("font_name")
            ASSStyle.Fontsize = subtitle.get("font_size")
            ASSStyle.PrimaryColour = subtitle.get("primary_color")
            ASSStyle.SecondaryColour = "&H000000FF"
            ASSStyle.OutlineColour = subtitle.get("border_color")
            ASSStyle.BackColour = subtitle.get("shadow_color")
            ASSStyle.Bold = subtitle.get("bold")
            ASSStyle.Italic = subtitle.get("italic")
            ASSStyle.Underline = subtitle.get("underline")
            ASSStyle.StrikeOut = subtitle.get("strikeout")
            ASSStyle.ScaleX = 100
            ASSStyle.ScaleY = 100
            ASSStyle.Spacing = 0
            ASSStyle.Angle = 0
            ASSStyle.BorderStyle = 1
            ASSStyle.Outline = subtitle.get("border")
            ASSStyle.Shadow = subtitle.get("shadow")
            ASSStyle.Alignment = subtitle.get("alignment")
            ASSStyle.MarginL = subtitle.get("marginL")
            ASSStyle.MarginR = subtitle.get("marginR")
            ASSStyle.MarginV = subtitle.get("marginV")
            ASSStyle.Encoding = 1

            return ASSStyle.to_string()

    class Cover:
        @classmethod
        def download(cls, task_info: DownloadTaskInfo):
            base_file_name = FileNameFormatter.format_file_basename(task_info)

            cover_type = Cover.get_cover_type()

            contents = Cover.download_cover(task_info.cover_url)

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

        @staticmethod
        def get_video_resolution(task_info: DownloadTaskInfo):
            data = DownloadParser.get_download_stream_json(task_info)

            width, height = Preview.get_video_resolution(task_info, data["video"])

            return {
                "width": width,
                "height": height
            }
