import math
import json
from io import BytesIO
from typing import List
from google.protobuf import json_format

from utils.auth.wbi import WbiUtils
from utils.common.model.data_type import DownloadTaskInfo
from utils.common.enums import DanmakuType

import utils.module.danmaku.dm_pb2 as dm_pb2

from utils.parse.extra.parser import Parser
from utils.parse.extra.file.danamku_xml import DanmakuXMLFile

class DanmakuParser(Parser):
    def __init__(self):
        Parser.__init__(self)

        self.task_info: DownloadTaskInfo = None
        self.base_file_name: str = ""

        self.buffers: List[BytesIO] = []

    def parse(self, task_info: DownloadTaskInfo):
        self.task_info = task_info

        self.buffers = self.get_all_protobuf_buffers()

        match DanmakuType(task_info):
            case DanmakuType.XML:
                task_info.output_type = "xml"
                self.generate_xml()
            
            case DanmakuType.Protobuf:
                task_info.output_type = "protobuf"
                self.generate_protobuf()

            case DanmakuType.JSON:
                task_info.output_type = "json"
                self.generate_json()

            case DanmakuType.ASS:
                task_info.output_type = "ass"
                self.generate_ass()

        self.task_info.total_file_size = self.total_file_size

    def generate_xml(self):
        json_data = self.get_all_protobuf_json_data(self.buffers)

        file = DanmakuXMLFile(json_data, self.task_info.cid)
        contents = file.get_contents()

        self.save_file(f"{self.task_info.file_name}.xml", contents, "w")

    def generate_protobuf(self):
        for index, buffer in enumerate(self.buffers):
            file_name = self.get_protobuf_file_name(len(self.buffers), index)

            self.save_file(file_name, buffer.getvalue(), "wb")

    def generate_json(self):
        json_data = self.get_all_protobuf_json_data(self.buffers)

        contents = json.dumps({
            "comments": json_data
        }, ensure_ascii = False, indent = 4)

        self.save_file(f"{self.task_info.file_name}.json", contents, "w")

    def generate_ass(self):
        pass

    def get_all_protobuf_buffers(self, task_info: DownloadTaskInfo):
        buffers = []

        if task_info.duration:
            segments = math.ceil(task_info.duration / 360)

            for i in range(segments):
                buffers.append(self.get_protobuf_data(task_info.cid, i))

        return buffers

    def get_all_protobuf_json_data(self, buffers: List[BytesIO]):
        json_data = []

        seg = dm_pb2.DmSegMobileReply()

        for buffer in buffers:
            seg.ParseFromString(buffer.getvalue())

            segment = [json_format.MessageToJson(entry) for entry in seg.elems]

            segment = [entry for entry in segment.copy() if entry.get("progress")]

            json_data.append(segment)

        json_data.sort(key = lambda x: x.get("progress"))

        return json_data

    def get_protobuf_data(self, cid: int, index: int):
        params = {
            "type": 1,
            "oid": cid,
            "segment_index": index
        }

        url = f"https://api.bilibili.com/x/v2/dm/wbi/web/seg.so?{WbiUtils.encWbi(params)}"

        return BytesIO(self.request_get(url).content)
    
    def get_protobuf_file_name(self, segments: int, index: int):
        if segments > 1:
            return f"{self.task_info.file_name}_part{index + 1}.protobuf"
        else:
            return f"{self.task_info.file_name}.protobuf"