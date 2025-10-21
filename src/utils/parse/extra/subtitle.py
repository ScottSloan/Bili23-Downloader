import json
from typing import List

from utils.config import Config
from utils.auth.wbi import WbiUtils

from utils.common.model.task_info import DownloadTaskInfo
from utils.common.enums import SubtitleLanOption, SubtitleType
from utils.common.formatter.formatter import FormatUtils

from utils.parse.extra.parser import Parser
from utils.parse.extra.file.subtitle_ass import SubtitleASSFile

class SubtitleParser(Parser):
    def __init__(self, task_info: DownloadTaskInfo):
        Parser.__init__(self)

        self.task_info = task_info

    def parse(self):
        url_list: List[dict] = self.get_all_subtitle_urls()

        for entry in url_list:
            language = entry.get("lan")

            if SubtitleLanOption(Config.Basic.subtitle_lan_option) == SubtitleLanOption.Custom:
                if language not in Config.Basic.subtitle_lan_custom_type:
                    continue

            url = "https:" + entry.get("subtitle_url")

            json_data = self.request_get(url, check = True)

            self.generate_subtitle(json_data, language)

        self.task_info.total_file_size += self.total_file_size

    def generate_subtitle(self, json_data: dict, language: str):
        match SubtitleType(self.task_info.extra_option.get("subtitle_file_type")):
            case SubtitleType.SRT:
                self.task_info.output_type = "srt"
                self.generate_srt(json_data, language)

            case SubtitleType.TXT:
                self.task_info.output_type = "txt"
                self.generate_txt(json_data, language)

            case SubtitleType.LRC:
                self.task_info.output_type = "lrc"
                self.generate_lrc(json_data, language)

            case SubtitleType.JSON:
                self.task_info.output_type = "json"
                self.generate_json(json_data, language)

            case SubtitleType.ASS:
                self.task_info.output_type = "ass"
                self.generate_ass(json_data, language)

    def generate_srt(self, json_data: dict, language: str):
        contents = ""

        for index, entry in enumerate(json_data["body"]):
            id = index + 1
            timestamp = FormatUtils.format_srt_line(entry["from"], entry["to"])
            content = entry["content"]

            contents += f"{id}\n{timestamp}\n{content}\n\n"

        self.save_file(f"{self.task_info.file_name}_{language}.srt", contents, "w")

    def generate_txt(self, json_data: dict, language: str):
        contents = ""

        for entry in json_data["body"]:
            content = entry["content"]

            contents += f"{content}\n"

        self.save_file(f"{self.task_info.file_name}_{language}.txt", contents, "w")

    def generate_lrc(self, json_data: dict, language: str):
        contents = ""

        for entry in json_data["body"]:
            timestamp = FormatUtils.format_lrc_line(entry["from"])
            content = entry["content"]

            contents += f"[{timestamp}]{content}\n"

        self.save_file(f"{self.task_info.file_name}_{language}.lrc", contents, "w")

    def generate_json(self, json_data: dict, language: str):
        contents = json.dumps(json_data, ensure_ascii = False, indent = 4)

        self.save_file(f"{self.task_info.file_name}_{language}.json", contents, "w")

    def generate_ass(self, json_data: dict, language: str):
        resolution = self.get_video_resolution()

        file = SubtitleASSFile(json_data, resolution)
        contents = file.get_contents()

        self.save_file(f"{self.task_info.file_name}_{language}.ass", contents, "w")

    def get_all_subtitle_urls(self):
        params = {
            "bvid": self.task_info.bvid,
            "cid": self.task_info.cid,
            "dm_img_list": "[]",
            "dm_img_str": "V2ViR0wgMS4wIChPcGVuR0wgRVMgMi4wIENocm9taXVtKQ",
            "dm_cover_img_str": "QU5HTEUgKE5WSURJQSwgTlZJRElBIEdlRm9yY2UgUlRYIDQwNjAgTGFwdG9wIEdQVSAoMHgwMDAwMjhFMCkgRGlyZWN0M0QxMSB2c181XzAgcHNfNV8wLCBEM0QxMSlHb29nbGUgSW5jLiAoTlZJRElBKQ",
            "dm_img_inter": '{"ds":[],"wh":[5231,6067,75],"of":[475,950,475]}',
        }

        url = f"https://api.bilibili.com/x/player/wbi/v2?{WbiUtils.encWbi(params)}"

        data = self.request_get(url, check = True)

        return data["data"]["subtitle"]["subtitles"]