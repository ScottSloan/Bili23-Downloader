import os
from datetime import datetime

from utils.config import Config
from utils.tool_v2 import UniversalTool

from utils.common.data_type import DownloadTaskInfo
from utils.common.map import video_quality_map, audio_quality_map, video_codec_short_map, get_mapping_key_by_value

class FileNameFormatter:
    @classmethod
    def format_file_name(cls, task_info: DownloadTaskInfo, template: str):
        field_dict = cls.get_field_dict(task_info)

        field_dict = cls.check_empty_field(field_dict)

        return template.format(**field_dict)

    @staticmethod
    def get_download_path():
        dirname = os.path.dirname(Config.Advanced.file_name_template)

        return os.path.join(Config.Download.path, dirname)
    
    @staticmethod
    def check_empty_field(field_dict: dict):
        for value in field_dict.values():
            if not value:
                value = "null"

        return field_dict

    @staticmethod
    def check_file_name_length(file_name: str, max_length: int = 255):
        base_name, ext = os.path.splitext(file_name)

        if len(base_name) + len(ext) > max_length:
            return base_name[:max_length - len(ext)] + ext
        
        return file_name

    @staticmethod
    def get_field_dict(task_info: DownloadTaskInfo):
        def get_pubdatetime():
            if task_info.pubtime:
                return datetime.fromtimestamp(task_info.pubtime).strftime(Config.Advanced.datetime_format)

        return {
            "datetime": datetime.now().strftime(Config.Advanced.datetime_format),
            "timestamp": str(int(datetime.now().timestamp())),
            "pubdatetime": get_pubdatetime(),
            "pubtimestamp": task_info.pubtime,
            "number": task_info.number,
            "zero_padding_number": task_info.zero_padding_number,
            "zone": task_info.tname_info.get("tname"),
            "subzone": task_info.tname_info.get("subtname"),
            "area": task_info.area,
            "title": UniversalTool.get_legal_name(task_info.title),
            "aid": task_info.aid,
            "bvid": task_info.bvid,
            "cid": task_info.cid,
            "ep_id": task_info.ep_id,
            "season_id": task_info.season_id,
            "media_id": task_info.media_id,
            "series_title": task_info.series_title,
            "video_quality": get_mapping_key_by_value(video_quality_map, task_info.video_quality_id),
            "audio_quality": get_mapping_key_by_value(audio_quality_map, task_info.audio_quality_id),
            "video_codec": get_mapping_key_by_value(video_codec_short_map, task_info.video_codec_id),
            "duration": task_info.duration,
            "up_name": task_info.up_info.get("up_name"),
            "up_mid": task_info.up_info.get("up_mid")
        }
