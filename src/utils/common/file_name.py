import os
from datetime import datetime

from utils.common.data_type import DownloadTaskInfo
from utils.common.map import video_quality_map, audio_quality_map, video_codec_short_map, get_mapping_key_by_value
from utils.tool_v2 import UniversalTool
from utils.config import Config

class FileNameManager:
    def __init__(self, task_info: DownloadTaskInfo):
        self.task_info = task_info

    def get_full_file_name(self, template: str, auto_adjust_field: bool):
        fields_dict = self.get_fields_dict()

        if auto_adjust_field:
            template = self.check_field_empty(template, fields_dict)

        return template.format(**fields_dict)
    
    def check_file_name_legnth(self, file_name: str):
        filename, ext = os.path.splitext(os.path.basename(file_name))

        if len(file_name) > 255:
            filename = filename[:255 - len(ext)]
        
        return filename + ext

    def check_field_empty(self, template: str, fields_dict: dict):
        for key, value in fields_dict.items():
            if not value:
                result = self.find_field(template, "{" + key + "}")

                if result:
                    template = template.replace(result, "")
        
        return template

    def get_fields_dict(self):
        return {
            "date": datetime.now().strftime(Config.Advanced.date_format),
            "time": datetime.now().strftime(Config.Advanced.time_format),
            "timestamp": str(int(datetime.now().timestamp())),
            "pubdate": datetime.fromtimestamp(self.task_info.pubtime).strftime(Config.Advanced.date_format),
            "pubtime": datetime.fromtimestamp(self.task_info.pubtime).strftime(Config.Advanced.time_format),
            "pubtimestamp": self.task_info.pubtime,
            "number": self.task_info.number,
            "number_with_zero": self.task_info.number_with_zero,
            "tname": self.task_info.tname_info.get("tname"),
            "tname_v2": self.task_info.tname_info.get("tname_v2"),
            "area": self.task_info.area,
            "title": UniversalTool.get_legal_name(self.task_info.title),
            "aid": self.task_info.aid,
            "bvid": self.task_info.bvid,
            "cid": self.task_info.cid,
            "video_quality": get_mapping_key_by_value(video_quality_map, self.task_info.video_quality_id),
            "audio_quality": get_mapping_key_by_value(audio_quality_map, self.task_info.audio_quality_id),
            "video_codec": get_mapping_key_by_value(video_codec_short_map, self.task_info.video_codec_id),
            "duration": self.task_info.duration,
            "up_name": self.task_info.up_info.get("up_name"),
            "up_mid": self.task_info.up_info.get("up_mid")
        }

    def find_field(self, string: str, field: str):
        target_field_index = string.find(field)
        before_target_field_index = string.rfind("}", 0, target_field_index)
        after_target_field_index = string.find("{", target_field_index + 1, len(string))

        if before_target_field_index == -1 and after_target_field_index != -1:
            start = 0
            end = after_target_field_index
        
        elif before_target_field_index != -1 and after_target_field_index != -1:
            start = target_field_index
            end = after_target_field_index
        
        else:
            start = before_target_field_index + 1
            end = len(string)

        return string[start:end]