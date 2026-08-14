from ...common.translator import Translator
from ...common.enum import SubtitleType
from ...common.config import config
from ...common._json import json_dumps

from ...network.request import SyncNetWorkRequest
from ...download.task.info import TaskInfo
from ...format.time import Time

from .base import AdditionalParserBase
from .file.subtitle_ass import SubtitlesASS

# B 站 AI 生成字幕的语言码前缀，如 ai-zh、ai-es
AI_LANGUAGE_PREFIX = "ai-"

# MKV 的 Language 元素期望 ISO 639-2 三字母码，而 B 站返回的是 BCP-47 风格的语言标签。
# 不做归一的话播放器只能原样显示 ai-es 这类非法码，字幕菜单会很难读
LANGUAGE_CODE_MAP = {
    "zh": "chi",
    "zh-cn": "chi",
    "zh-hans": "chi",
    "zh-hant": "chi",
    "zh-hk": "chi",
    "zh-tw": "chi",
    "en": "eng",
    "en-us": "eng",
    "en-gb": "eng",
    "ja": "jpn",
    "jp": "jpn",
    "ko": "kor",
    "es": "spa",
    "ar": "ara",
    "pt": "por",
    "fr": "fre",
    "de": "ger",
    "ru": "rus",
    "it": "ita",
    "vi": "vie",
    "th": "tha",
    "id": "ind",
    "ms": "may",
    "hi": "hin",
    "tr": "tur",
    "pl": "pol",
    "nl": "dut",
    "tl": "tgl"
}

class SubtitlesParser(AdditionalParserBase):
    def __init__(self, task_info: TaskInfo):
        super().__init__(task_info)

    def parse(self, player_data: dict):
        subtitles_data_list = self._get_subtitles_data_list(player_data)

        subtitle_type = config.get(config.subtitle_type)

        for entry in subtitles_data_list:
            language = entry["language"]
            data = entry["data"]

            match subtitle_type:
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

            file_name = self._write(contents, suffix = suffix, name = self.task_info.File.name, qualifier = [Translator.ADDITIONAL_FILES_QUALIFIER("SUBTITLES"), language])

            self._check_embed_subtitle(subtitle_type, file_name, entry)

    def _check_embed_subtitle(self, subtitle_type: SubtitleType, file_name: str, entry: dict):
        # 仅 ASS 格式能作为字幕轨嵌入，其余格式即便开着开关也静默跳过
        if subtitle_type != SubtitleType.ASS:
            return

        if not config.get(config.embed_subtitle) or not self.is_embed_available(self.task_info):
            return

        self._add_subtitle_track(
            file_name,
            title = self._get_track_title(entry),
            language = self._to_iso_639_2(entry["language"]),
            kind = "subtitle"
        )

    def _get_track_title(self, entry: dict):
        # B 站对 AI 字幕的 lan_doc 就是纯语言名，与人工字幕完全一样，
        # 只有 lan 里的 ai- 前缀能区分两者。不标注的话播放器菜单里会出现两条同名的「中文」
        title = entry["language_doc"]

        if entry["language"].lower().startswith(AI_LANGUAGE_PREFIX):
            return Translator.SUBTITLE_TRACK_TITLE("AI_GENERATED").format(name = title)

        return title

    def _to_iso_639_2(self, language: str):
        key = language.lower()

        if code := LANGUAGE_CODE_MAP.get(key):
            return code

        # AI 字幕的语言码形如 ai-zh、ai-es，剥掉前缀后再查一次
        if key.startswith(AI_LANGUAGE_PREFIX):
            if code := LANGUAGE_CODE_MAP.get(key[len(AI_LANGUAGE_PREFIX):]):
                return code

        # 表中没有的原样传给 FFmpeg，不用 und 兜底，避免丢掉已知的语言信息
        return language

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
        return json_dumps(data, indent = 2), "json"

    def _get_subtitles_data_list(self, player_data: dict):
        subtitles_data_list = []

        subtitles_url_list = player_data.get("subtitle", {}).get("subtitles", [])
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
                    # lan_doc 是「中文（简体）」这类可读名称，用作嵌入后的字幕轨标题
                    "language_doc": entry.get("lan_doc") or language,
                    "data": data,
                })

        return subtitles_data_list

    def _get_subtitles_data(self, url: str):
        request = SyncNetWorkRequest(url)
        response = request.run()

        return response
