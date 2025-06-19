import os
import re
from datetime import datetime

from utils.config import Config

from utils.common.data_type import DownloadTaskInfo
from utils.common.map import video_quality_map, audio_quality_map, video_codec_short_map, get_mapping_key_by_value
from utils.common.enums import ParseType, ScopeID

class FileNameFormatter:
    @classmethod
    def format_file_name(cls, task_info: DownloadTaskInfo, template: str = None, basename: bool = True):
        if not template:
            template = cls.get_template(task_info)

        field_dict = cls.check_empty_field(cls.get_field_dict(task_info))

        result = cls.removeprefix(cls.get_legal_file_name(template.format(**field_dict)))

        return os.path.basename(result) if basename else result

    @classmethod
    def get_download_path(cls, task_info: DownloadTaskInfo):
        def check_path(path: str):
            if not os.path.exists(path):
                os.makedirs(path)

        field_dict = cls.get_field_dict(task_info)

        dirname = os.path.dirname(cls.get_template(task_info))

        formatted = cls.removeprefix(dirname.format(**field_dict))

        path = os.path.join(Config.Download.path, cls.get_legal_file_name(formatted))

        check_path(path)

        return path
    
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
    def get_template(task_info: DownloadTaskInfo):
        def get_specific_template(scope_id) -> str:
            for entry in Config.Download.file_name_template_list:
                if entry["scope"] == scope_id:
                    return entry["template"]
                
        template = get_specific_template(ScopeID.All.value)
        
        if template:
            return template
        else:
            match ParseType(task_info.parse_type):
                case ParseType.Video:
                    template = get_specific_template(ScopeID.Video.value)

                case ParseType.Bangumi:
                    template = get_specific_template(ScopeID.Bangumi.value)

                case ParseType.Cheese:
                    template = get_specific_template(ScopeID.Cheese.value)

        if template:
            return template
        else:
            return get_specific_template(ScopeID.Default.value)

    @staticmethod
    def get_field_dict(task_info: DownloadTaskInfo):
        def check(data: dict):
            for value in data.values():
                if not value:
                    value = None
            
            return data

        return check({
            "time": datetime.now(),
            "timestamp": str(int(datetime.now().timestamp())),
            "pubtime": datetime.fromtimestamp(task_info.pubtime),
            "pubtimestamp": task_info.pubtime,
            "number": task_info.number,
            "zero_padding_number": task_info.zero_padding_number,
            "zone": task_info.zone_info.get("zone"),
            "subzone": task_info.zone_info.get("subzone"),
            "area": task_info.area,
            "title": FileNameFormatter.get_legal_file_name(task_info.title),
            "aid": task_info.aid,
            "bvid": task_info.bvid,
            "cid": task_info.cid,
            "ep_id": task_info.ep_id,
            "season_id": task_info.season_id,
            "media_id": task_info.media_id,
            "series_title": task_info.series_title,
            "section_title": task_info.section_title,
            "part_title": task_info.part_title,
            "list_title": task_info.list_title,
            "video_quality": get_mapping_key_by_value(video_quality_map, task_info.video_quality_id),
            "audio_quality": get_mapping_key_by_value(audio_quality_map, task_info.audio_quality_id),
            "video_codec": get_mapping_key_by_value(video_codec_short_map, task_info.video_codec_id),
            "duration": task_info.duration,
            "up_name": task_info.up_info.get("up_name"),
            "up_mid": task_info.up_info.get("up_mid")
        })

    @staticmethod
    def get_legal_file_name(file_name: str):
        return re.sub(r'[:*?"<>|]', "_", file_name)
    
    @staticmethod
    def removeprefix(path: str):
        while path.startswith("\\"):
            path = path.removeprefix("\\")

        return path