import random

from utils.config import Config

from utils.common.model.data_type import TreeListItemInfo
from utils.common.model.task_info import DownloadTaskInfo
from utils.common.enums import ParseType

class DownloadInfo:
    @classmethod
    def get_download_info(cls, item_info: TreeListItemInfo):
        download_info_list = []

        info = cls.get_base_download_info(item_info)

        if Config.Download.stream_download_option:
            info = cls.get_download_params_info(info)

            download_info_list.append(cls.get_task_info_obj(info))

        if Config.Basic.download_danmaku_file or Config.Basic.download_subtitle_file or Config.Basic.download_cover_file:
            info = cls.get_extra_download_info(info)

            download_info_list.append(cls.get_task_info_obj(info))

        return download_info_list
    
    @staticmethod
    def get_base_download_info(item_info: TreeListItemInfo):
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
            "title": item_info.title,
            "section_title": item_info.section_title,
            "part_title": item_info.part_title,
            "collection_title": item_info.collection_title,
            "series_title": item_info.series_title,
            "interact_title": item_info.interact_title,
            "parent_title": item_info.parent_title,
            "bangumi_type": item_info.bangumi_type,
            "template_type": item_info.template_type,
            "badge": item_info.badge,
            "page": item_info.page,
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
            "cover_file_type": Config.Basic.cover_file_type
        }
        info["video_width"] = Config.Temp.video_width
        info["video_height"] = Config.Temp.video_height

        return info
    
    @staticmethod
    def get_task_info_obj(info: dict):
        task_info = DownloadTaskInfo()
        task_info.load_from_dict(info)

        task_info.id = random.randint(10000000, 99999999)

        return task_info