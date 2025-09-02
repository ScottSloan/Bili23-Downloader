import os
import re

from utils.config import Config

from utils.common.model.data_type import DownloadTaskInfo
from utils.common.map import video_quality_map, audio_quality_map, video_codec_short_map, get_mapping_key_by_value
from utils.common.enums import TemplateType
from utils.common.datetime_util import DateTime
from utils.common.io.directory import Directory

class FileNameFormatter:
    @classmethod
    def format_file_name(cls, template: str, task_info: DownloadTaskInfo = None, field_dict: dict = None):
        if not field_dict:
            field_dict = cls.get_field_dict(task_info)

        file_name = template.format(**field_dict)

        return cls.check_slash(file_name)
    
    @classmethod
    def format_file_basename(cls, task_info: DownloadTaskInfo):
        template = cls.get_template(task_info)

        return os.path.basename(cls.format_file_name(template, task_info = task_info))

    @classmethod
    def get_download_path(cls, task_info: DownloadTaskInfo):
        field_dict = cls.get_field_dict(task_info)
        template = cls.get_template(task_info)

        template_path = template.format(**field_dict)

        path = os.path.join(task_info.download_base_path, task_info.parent_title, cls.check_slash(template_path))
        
        download_path = os.path.dirname(path)

        Directory.create_directory(download_path)

        return download_path

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

    @classmethod
    def get_template(cls, task_info: DownloadTaskInfo) -> str:
        template = cls.get_specific_template(task_info.template_type)

        if not template:
            template = cls.get_specific_template(TemplateType.Video_Normal.value)

        return template

    @staticmethod
    def get_field_dict(task_info: DownloadTaskInfo):
        def check(data: dict):
            for value in data.values():
                if not value:
                    value = None
            
            return data

        return check({
            "time": DateTime.now(),
            "timestamp": str(DateTime.get_timestamp()),
            "pubtime": DateTime.from_timestamp(task_info.pubtimestamp),
            "pubtimestamp": task_info.pubtimestamp,
            "number": task_info.number,
            "zero_padding_number": task_info.zero_padding_number,
            "page": task_info.page,
            "zone": task_info.zone,
            "subzone": task_info.subzone,
            "area": task_info.area,
            "title": FileNameFormatter.get_legal_file_name(task_info.title),
            "aid": task_info.aid,
            "bvid": task_info.bvid,
            "cid": task_info.cid,
            "ep_id": task_info.ep_id,
            "season_id": task_info.season_id,
            "media_id": task_info.media_id,
            "series_title": FileNameFormatter.get_legal_file_name(task_info.series_title),
            "section_title": FileNameFormatter.get_legal_file_name(task_info.section_title),
            "part_title": FileNameFormatter.get_legal_file_name(task_info.part_title),
            "collection_title": FileNameFormatter.get_legal_file_name(task_info.collection_title),
            "interact_title": FileNameFormatter.get_legal_file_name(task_info.interact_title),
            "badge": task_info.badge,
            "episode_num": task_info.episode_num,
            "bangumi_type": task_info.bangumi_type,
            "video_quality": get_mapping_key_by_value(video_quality_map, task_info.video_quality_id),
            "audio_quality": get_mapping_key_by_value(audio_quality_map, task_info.audio_quality_id),
            "video_codec": get_mapping_key_by_value(video_codec_short_map, task_info.video_codec_id),
            "duration": task_info.duration,
            "up_name": FileNameFormatter.get_legal_file_name(task_info.up_name),
            "up_uid": task_info.up_uid
        })

    @staticmethod
    def get_legal_file_name(file_name: str):
        escape = re.sub(r'[\r\n\t]', "", file_name)

        return re.sub(r'[:*?"<>|\\/]', "_", escape)
    
    @staticmethod
    def check_slash(path: str):
        path = path.lstrip("\\/").rstrip("\\/")
        path = path.replace("/", os.sep)

        return path
    
    @staticmethod
    def get_specific_template(template_type: int):        
        for entry in Config.Download.file_name_template_list:
            if entry["type"] == template_type:
                return entry["template"]