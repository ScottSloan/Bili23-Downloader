import random

from utils.config import Config

from utils.common.model.list_item_info import TreeListItemInfo
from utils.common.model.task_info import DownloadTaskInfo
from utils.common.enums import ParseType, TemplateType
from utils.common.formatter.strict_naming import StrictNaming

class DownloadInfo:
    @classmethod
    def get_download_info(cls, item_info: TreeListItemInfo):
        download_info_list = []

        info = cls.get_base_download_info(item_info)

        if Config.Download.stream_download_option:
            info = cls.get_download_params_info(info)

            download_info_list.append(cls.get_task_info_obj(info))

        download_extra_option = Config.Basic.download_danmaku_file or Config.Basic.download_subtitle_file or Config.Basic.download_cover_file or Config.Basic.download_metadata_file

        if download_extra_option:
            info = cls.get_extra_download_info(info)

            download_info_list.append(cls.get_task_info_obj(info))

        return download_info_list
    
    @classmethod
    def get_base_download_info(cls, item_info: TreeListItemInfo):
        return {
            "list_number": item_info.number,
            "cover_url": item_info.cover_url,
            "duration": item_info.duration,
            "aid": item_info.aid,
            "cid": item_info.cid,
            "bvid": item_info.bvid,
            "ep_id": item_info.ep_id,
            "season_id": item_info.season_id,
            "media_id": item_info.media_id,
            "pubtimestamp": item_info.pubtime,
            "episode_num": item_info.episode_num,
            "season_num": item_info.season_num,
            "title": item_info.title,
            "section_title": item_info.section_title,
            "part_title": item_info.part_title,
            "collection_title": item_info.collection_title,
            "series_title": item_info.series_title,
            "interact_title": item_info.interact_title,
            "parent_title": item_info.parent_title,
            "series_title_original": item_info.series_title_original,
            "bangumi_type": item_info.bangumi_type,
            "template_type": item_info.template_type,
            "template": cls.get_specific_template(item_info.template_type)["0"],
            "area": item_info.area,
            "zone": item_info.zone,
            "subzone": item_info.subzone,
            "badge": item_info.badge,
            "page": item_info.page,
            "total_count": item_info.total_count,
            "referer_url": "https://www.bilibili.com/",
            "up_name": item_info.up_name,
            "up_uid": item_info.up_mid,
            "parse_type": item_info.type,
            "download_type": item_info.type,
            "download_base_path": Config.Download.path
        }
    
    @staticmethod
    def get_download_params_info(info: dict):
        info["download_option"] = Config.Download.stream_download_option
        info["video_quality_id"] = Config.Download.video_quality_id
        info["audio_quality_id"] = Config.Download.audio_quality_id
        info["video_codec_id"] = Config.Download.video_codec_id
        info["further_processing"] = True
        info["ffmpeg_merge"] = Config.Download.ffmpeg_merge

        return info

    @staticmethod
    def get_extra_download_info(info: dict):
        info["download_type"] = ParseType.Extra.value
        info["video_quality_id"] = Config.Download.video_quality_id
        info["further_processing"] = False
        info["ffmpeg_merge"] = False
        info["extra_option"] = {
            "download_danmaku_file": Config.Basic.download_danmaku_file,
            "danmaku_file_type": Config.Basic.danmaku_file_type,
            "download_subtitle_file": Config.Basic.download_subtitle_file,
            "subtitle_file_type": Config.Basic.subtitle_file_type,
            "download_cover_file": Config.Basic.download_cover_file,
            "cover_file_type": Config.Basic.cover_file_type,
            "download_metadata_file": Config.Basic.download_metadata_file,
            "metadata_file_type": Config.Basic.metadata_file_type
        }
        info["video_width"] = Config.Temp.video_width
        info["video_height"] = Config.Temp.video_height

        return info
    
    @classmethod
    def get_task_info_obj(cls, info: dict):
        task_info = DownloadTaskInfo()
        task_info.load_from_dict(info)

        task_info.id = random.randint(10000000, 99999999)

        cls.check_strict_naming(task_info)

        return task_info
    
    @classmethod
    def check_strict_naming(cls, task_info: DownloadTaskInfo):
        if ParseType(task_info.parse_type) == ParseType.Bangumi and Config.Download.strict_naming:
            if task_info.season_num:
                StrictNaming.check_strict_naming(task_info)

                task_info.template_type = TemplateType.Bangumi_strict.value

                template = cls.get_specific_template(task_info.template_type)
                if task_info.section_title == "正片":
                    task_info.template = template["0"]
                else:
                    task_info.template = template["1"]

    @staticmethod
    def get_specific_template(template_type: int):
        for entry in Config.Download.file_name_template_list:
            if entry["type"] == template_type:
                return entry["template"]