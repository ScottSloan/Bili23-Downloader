from util.parse.additional import DanmakuXML, DanmakuASS, AdditionalParserBase
from util.network import ResponseType, SyncNetWorkRequest
from util.common import config, Translator
from util.common.enum import DanmakuType
from util.misc import dm_pb2

from ...download.task.info import TaskInfo

from google.protobuf.json_format import MessageToDict
from typing import List
from math import ceil
import json

class DanmakuParser(AdditionalParserBase):
    def __init__(self, task_info: TaskInfo):
        super().__init__(task_info)

    def parse(self):
        dict_list = self._get_all_protobuf_parts()

        match config.get(config.danmaku_type):
            case DanmakuType.XML:
                contents, suffix = self._to_xml(dict_list)

            case DanmakuType.ASS:
                contents, suffix = self._to_ass(dict_list)

            case DanmakuType.JSON:
                contents, suffix = self._to_json(dict_list)

        self._write(contents, suffix = suffix, name = self.task_info.File.name, qualifier = [Translator.ADDITIONAL_FILES_QUALIFIER("DANMAKU")])

    def _to_xml(self, dict_list: List[dict]) -> tuple:
        xml = DanmakuXML(dict_list, self.task_info.Episode.cid).generate()

        return xml, "xml"

    def _to_ass(self, dict_list: List[dict]) -> tuple:
        ass = DanmakuASS(dict_list, self.task_info.Basic.show_title).generate()

        return ass, "ass"

    def _to_json(self, dict_list: List[dict]) -> tuple:
        return json.dumps(dict_list, ensure_ascii = False, indent = 2), "json"

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
        # 将所有 protobuf 数据转换为 dict 格式，方便后续处理
        dict_list = []

        for segment in segment_list:
            DmSeg = dm_pb2.DmSegMobileReply()
            DmSeg.ParseFromString(segment)

            temp_entry = MessageToDict(DmSeg).get("elems", [])

            # 过滤无效的弹幕数据
            dict_list.extend([entry for entry in temp_entry if entry.get("stime") and entry.get("text")])

        return dict_list