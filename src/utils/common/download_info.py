import random

from utils.config import Config

from utils.common.data_type import TreeListItemInfo, DownloadTaskInfo
from utils.common.enums import ParseType

from utils.parse.video import VideoInfo
from utils.parse.bangumi import BangumiInfo
from utils.parse.cheese import CheeseInfo
from utils.parse.audio import AudioInfo

class DownloadInfo:
    @classmethod
    def get_download_info(cls, item_info: TreeListItemInfo, parse_type: ParseType, video_quality_id: int, video_codec_id: int):
        download_info_list = []

        info = cls.get_media_download_info(item_info, parse_type)

        if Config.Download.stream_download_option:
            info = cls.get_download_params_info(info, video_quality_id, video_codec_id)

            download_info_list.append(cls.get_task_info_obj(info))

        if Config.Basic.download_danmaku_file or Config.Basic.download_subtitle_file or Config.Basic.download_cover_file:
            info = cls.get_extra_download_info(info, video_quality_id)

            download_info_list.append(cls.get_task_info_obj(info))

        return download_info_list
    
    @classmethod
    def get_media_download_info(cls, item_info: TreeListItemInfo, parse_type: ParseType):
        match parse_type:
            case ParseType.Video:
                info = cls.get_video_download_info(item_info)

            case ParseType.Bangumi:
                info = cls.get_bangumi_download_info(item_info)

            case ParseType.Cheese:
                info = cls.get_cheese_download_info(item_info)
        
        info["download_base_path"] = Config.Download.path

        return info
    
    @classmethod
    def get_video_download_info(cls, item_info: TreeListItemInfo):
        info = cls.get_base_download_info(item_info)

        info["parse_type"] = ParseType.Video.value
        info["download_type"] = ParseType.Video.value
        info["zone_info"] = {
            "zone": VideoInfo.zone,
            "subzone": VideoInfo.subzone
        }
        info["up_info"] = {
            "up_name": VideoInfo.up_name,
            "up_mid": VideoInfo.up_mid
        }

        return info
    
    @classmethod
    def get_bangumi_download_info(cls, item_info: TreeListItemInfo):
        info = cls.get_base_download_info(item_info)

        info["parse_type"] = ParseType.Bangumi.value
        info["download_type"] = ParseType.Bangumi.value
        info["area"] = BangumiInfo.area
        info["series_title"] = BangumiInfo.series_title
        info["up_info"] = {
            "up_name": BangumiInfo.up_name,
            "up_mid": BangumiInfo.up_mid
        }

        return info

    @classmethod
    def get_cheese_download_info(cls, item_info: TreeListItemInfo):
        info = cls.get_base_download_info(item_info)

        info["parse_type"] = ParseType.Cheese.value
        info["download_type"] = ParseType.Cheese.value
        info["series_title"] = CheeseInfo.title
        info["up_info"] = {
            "up_name": CheeseInfo.up_name,
            "up_mid": CheeseInfo.up_mid
        }

        return info
    
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
            "pubtime": item_info.pubtime,
            "title": item_info.title,
            "section_title": item_info.section_title,
            "part_title": item_info.part_title,
            "list_title": item_info.list_title,
            "referer_url": "https://www.bilibili.com"
        }
    
    @staticmethod
    def get_download_params_info(info: dict, video_quality_id: int, video_codec_id: int):
        info["download_option"] = Config.Download.stream_download_option
        info["video_quality_id"] = video_quality_id
        info["audio_quality_id"] = AudioInfo.audio_quality_id
        info["video_codec_id"] = video_codec_id
        info["further_processing"] = True
        info["ffmpeg_merge"] = Config.Download.ffmpeg_merge

        return info

    @staticmethod
    def get_extra_download_info(info: dict, video_quality_id: int):
        info["download_type"] = ParseType.Extra.value
        info["video_quality_id"] = video_quality_id
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

        return info
    
    @staticmethod
    def get_task_info_obj(info: dict):
        task_info = DownloadTaskInfo()
        task_info.load_from_dict(info)

        task_info.id = random.randint(10000000, 99999999)

        return task_info