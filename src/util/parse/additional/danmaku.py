from ...network.request import ResponseType, SyncNetWorkRequest
from ...download.task.info import TaskInfo
from ...common.translator import Translator
from ...common._json import dumps
from ...common.enum import DanmakuType, DanmakuSuffixMode
from ...download.task.options import resolve

from .base import AdditionalParserBase
from .file.danmaku_ass import DanmakuASS
from .file.danmaku_xml import DanmakuXML

import util.misc.dm_pb2 as dm_pb2

import re
from typing import List
from math import ceil

class DanmakuParser(AdditionalParserBase):
    def __init__(self, task_info: TaskInfo):
        super().__init__(task_info)

    def parse(self):
        dict_list = self._get_all_protobuf_parts()

        danmaku_type = resolve(self.task_info, "danmaku_type")

        match danmaku_type:
            case DanmakuType.XML:
                contents, suffix = self._to_xml(dict_list)

            case DanmakuType.ASS:
                contents, suffix = self._to_ass(dict_list)

            case DanmakuType.JSON:
                contents, suffix = self._to_json(dict_list)

        suffix_mode = resolve(self.task_info, "danmaku_suffix_mode")
        custom_suffix = resolve(self.task_info, "custom_danmaku_suffix")
        qualifier = self.resolve_qualifier(suffix_mode, custom_suffix)

        file_name = self._write(contents, suffix = suffix, name = self.task_info.File.name, qualifier = qualifier)

        self._check_embed_danmaku(danmaku_type, file_name)

    @staticmethod
    def resolve_qualifier(mode: DanmakuSuffixMode, custom_suffix: str = "") -> List[str]:
        match mode:
            case DanmakuSuffixMode.NONE:
                return []

            case DanmakuSuffixMode.CUSTOM:
                # 路径非法字符替换为下划线，并去除首尾空格与点号
                cleaned = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", custom_suffix or "")
                cleaned = cleaned.strip(" .")
                # 合并连续的点 (e.g. "a..b" -> "a.b")
                cleaned = re.sub(r"\.{2,}", ".", cleaned)

                return [cleaned] if cleaned else []

            case _:
                return [Translator.ADDITIONAL_FILES_QUALIFIER("DANMAKU")]

    def _check_embed_danmaku(self, danmaku_type: DanmakuType, file_name: str):
        # 仅 ASS 格式能作为字幕轨嵌入，其余格式即便开着开关也静默跳过
        if danmaku_type != DanmakuType.ASS:
            return

        if not resolve(self.task_info, "embed_danmaku") or not self.is_embed_available(self.task_info):
            return

        self._add_subtitle_track(
            file_name,
            title = Translator.ADDITIONAL_FILES_QUALIFIER("DANMAKU"),
            kind = "danmaku"
        )

    def _to_xml(self, dict_list: List[dict]) -> tuple:
        xml = DanmakuXML(dict_list, self.task_info.Episode.cid).generate()

        return xml, "xml"

    def _to_ass(self, dict_list: List[dict]) -> tuple:
        ass = DanmakuASS(dict_list, self.task_info.Basic.show_title).generate()

        return ass, "ass"

    def _to_json(self, dict_list: List[dict]) -> tuple:
        return dumps(dict_list, indent = 2), "json"

    def _get_all_protobuf_parts(self):
        if duration := self.task_info.Episode.duration:
            segment_list = []

            # 每6分钟一包，向上取整
            parts = ceil(duration / 360)

            for index in range(1, parts + 1):
                segment_list.append(self._get_protobuf_danmaku(self.task_info.Episode.cid, index))

            return self._proto_to_dict_list(segment_list)
        
        return []

    def _get_protobuf_danmaku(self, cid: int, index: int):
        params = {
            "type": 1,
            "oid": cid,
            "segment_index": index
        }

        url = f"https://api.bilibili.com/x/v2/dm/wbi/web/seg.so?{self.enc_wbi(params)}"

        request = SyncNetWorkRequest(url, response_type = ResponseType.BYTES)
        response = request.run()

        return response

    def _proto_to_dict_list(self, segment_list: List[bytes]) -> List[dict]:
        from google.protobuf.json_format import MessageToDict
        
        # 将所有 protobuf 数据转换为 dict 格式，方便后续处理
        dict_list = []

        for segment in segment_list:
            DmSeg = dm_pb2.DmSegMobileReply()
            DmSeg.ParseFromString(segment)

            temp_entry = MessageToDict(DmSeg).get("elems", [])

            # 过滤无效的弹幕数据
            dict_list.extend([entry for entry in temp_entry if entry.get("stime") and entry.get("text")])

        return dict_list