from util.parse.additional import SubtitlesASS, AdditionalParserBase
from util.network import SyncNetWorkRequest
from util.common import config, Translator
from util.common.enum import SubtitleType
from util.format.time import Time

from ...download.task.info import TaskInfo

import json

class SubtitlesParser(AdditionalParserBase):
    def __init__(self, task_info: TaskInfo):
        super().__init__(task_info)

    def parse(self):
        subtitles_data_list = self._get_subtitles_data_list()

        for entry in subtitles_data_list:
            language = entry["language"]
            data = entry["data"]

            match config.get(config.subtitle_type):
                case SubtitleType.SRT:
                    contents, suffix = self._to_srt(data)

                case SubtitleType.LRC:
                    contents, suffix = self._to_lrc(data)
                
                case SubtitleType.TXT:
                    contents, suffix = self._to_txt(data)

                case SubtitleType.ASS:
                    contents, suffix = self._to_ass(data)

                case SubtitleType.JSON:
                    contents, suffix = self._to_json(data)

            self._write(contents, suffix = suffix, name = self.task_info.File.name, qualifier = [Translator.ADDITIONAL_FILES_QUALIFIER("SUBTITLES"), language])

    def _to_srt(self, data: dict):
        srt_lines = []
        
        for i, item in enumerate(data.get("body", [])):
            start = item.get("from", 0)
            end = item.get("to", 0)
            content = item.get("content", "")
            
            srt_lines.append(f"{i + 1}")
            srt_lines.append(f"{Time.format_srt_time(start)} --> {Time.format_srt_time(end)}")
            srt_lines.append(f"{content}\n")
            
        return "\n".join(srt_lines).strip(), "srt"

    def _to_lrc(self, data: dict):
        lrc_lines = []

        for item in data.get("body", []):
            start = item.get("from", 0)
            content = item.get("content", "")
            
            m = int(start // 60)
            s = start % 60
            
            lrc_lines.append(f"[{m:02d}:{s:05.2f}]{content}")
            
        return "\n".join(lrc_lines).strip(), "lrc"

    def _to_txt(self, data: dict):
        txt_lines = []

        for item in data.get("body", []):
            content = item.get("content", "")
            txt_lines.append(content)

        return "\n".join(txt_lines).strip(), "txt"

    def _to_ass(self, data: dict):
        ass = SubtitlesASS(data, self.task_info.Basic.show_title).generate()

        return ass, "ass"

    def _to_json(self, data: dict):
        return json.dumps(data, ensure_ascii = False, indent = 2), "json"

    def _get_subtitles_data_list(self):
        subtitles_data_list = []

        subtitles_url_list = self._get_subtitles_url_list()
        language_config = config.get(config.subtitle_language)

        for entry in subtitles_url_list:
            language = entry["lan"]

            if language_config["download_specified"]:
                if language not in language_config["specified_language"]:
                    continue

            url = f"https:{entry.get('subtitle_url')}"

            data = self._get_subtitles_data(url)

            if data:
                subtitles_data_list.append({
                    "language": language,
                    "data": data,
                })

        return subtitles_data_list

    def _get_subtitles_data(self, url: str):
        request = SyncNetWorkRequest(url)
        response = request.run()

        return response

    def _get_subtitles_url_list(self):
        params = {
            "bvid": self.task_info.Episode.bvid,
            "cid": self.task_info.Episode.cid,
            "dm_img_list": "[]",
            "dm_img_str": "V2ViR0wgMS4wIChPcGVuR0wgRVMgMi4wIENocm9taXVtKQ",
            "dm_cover_img_str": "QU5HTEUgKE5WSURJQSwgTlZJRElBIEdlRm9yY2UgUlRYIDQwNjAgTGFwdG9wIEdQVSAoMHgwMDAwMjhFMCkgRGlyZWN0M0QxMSB2c181XzAgcHNfNV8wLCBEM0QxMSlHb29nbGUgSW5jLiAoTlZJRElBKQ",
            "dm_img_inter": '{"ds":[],"wh":[5231,6067,75],"of":[475,950,475]}',
        }
        
        url = f"https://api.bilibili.com/x/player/wbi/v2?{self.enc_wbi(params)}"

        request = SyncNetWorkRequest(url)
        response = request.run()

        return response["data"]["subtitle"]["subtitles"]
    