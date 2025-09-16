import os
import json
from typing import List

from utils.config import Config
from utils.common.io.file import File
from utils.common.enums import DownloadStatus

class DownloadTaskInfo:
    def __init__(self):
        # 最低支持版本
        self.min_version: int = 0

        # id，区分不同下载任务的唯一标识符
        self.id: int = 0
        # 序号
        self.number: int = 0
        # 补零序号
        self.zero_padding_number: str = ""
        # 列表中的序号
        self.list_number: int = 0
        # 时间戳
        self.timestamp: int = 0
        # 分P序号
        self.page: int = 0
        
        # Referer URL
        self.referer_url: str = ""
        # 视频封面链接
        self.cover_url: str = ""

        # 视频 bvid 和 cid 信息
        self.bvid: str = ""
        self.cid: int = 0
        self.aid: int = 0
        self.ep_id: int = 0
        self.season_id: int = 0
        self.media_id: int = 0

        # 视频标题
        self.title: str = ""
        # 剧集系列名称
        self.series_title: str = ""
        # 章节标题
        self.section_title: str = ""
        # 分节标题
        self.part_title: str = ""
        # 合集标题
        self.collection_title: str = ""
        # 互动视频标题
        self.interact_title: str = ""
        # parent_title
        self.parent_title: str = ""

        # 视频时长
        self.duration: int = 0

        # 下载目录
        self.download_base_path: str = ""
        # 完整下载目录
        self.download_path: str = ""
        # 下载文件名
        self.file_name: str = ""
        # 下载进度
        self.progress: int = 0
        # 总大小，单位字节
        self.total_file_size: int = 0
        # 已下载完成的总大小，单位字节
        self.total_downloaded_size: int = 0
        # 已下载完成的当前任务大小
        self.current_downloaded_size: int = 0
        # 下载状态
        self.status: int = DownloadStatus.Waiting.value

        # 媒体信息，0 表示未定义
        self.video_quality_id: int = 0
        self.audio_quality_id: int = 00
        self.video_codec_id: int = 0
        self.video_type: str = ""
        self.audio_type: str = ""
        self.output_type: str = ""

        # 下载项目标识
        self.download_items: list = []

        # 解析类型
        self.parse_type: int = 0
        # 下载类型
        self.download_type: int = 0
        # 视频流类型
        self.stream_type: int = 0
        # 下载选项
        self.download_option: List[int] = []
        # 是否调用 FFmpeg 合并
        self.ffmpeg_merge: bool = False
        # 下载完成后是否对文件进行进一步处理
        self.further_processing = False
        # flv 视频个数，仅 flv 流时有效
        self.flv_video_count: int = 0

        # 附加内容选项
        self.extra_option: dict = {}

        # 视频发布时间戳
        self.pubtimestamp: int = 0
        # 地区
        self.area: str = ""
        # 分区信息
        self.zone: str = ""
        # 子分区信息
        self.subzone: str = ""
        # UP 主名称
        self.up_name: str = ""
        # UP 主uid
        self.up_uid: int = 0
        # 标识
        self.badge: str = ""
        # 季编号
        self.season_num: int = 0
        # 集编号
        self.episode_num: int = 0
        # 剧集类型
        self.bangumi_type: str = ""
        # 模板类型
        self.template_type: int = 0
        # 模板
        self.template: str = ""
        # 正片视频个数
        self.total_count: int = 0

        # 视频宽度
        self.video_width: int = 0
        self.video_height: int = 0

        # 源
        self.source: str = ""

        self.thread_info: dict = {}
        self.error_info: dict = {}

        # 元数据额外信息，不保存到文件
        # 标签
        self.tags: List[str] = []
        # UP 主头像
        self.up_face_url: str = ""
        # 视频简介
        self.description: str = ""
        # 演员列表
        self.actors: str = ""

    def to_dict(self):
        return {
            "min_version": self.min_version,

            "id": self.id,
            "number": self.number,
            "zero_padding_number": self.zero_padding_number,
            "list_number": self.list_number,
            "timestamp": self.timestamp,
            "page": self.page,

            "referer_url": self.referer_url,
            "cover_url": self.cover_url,

            "bvid": self.bvid,
            "cid": self.cid,
            "aid": self.aid,
            "ep_id": self.ep_id,
            "season_id": self.season_id,
            "media_id": self.media_id,

            "title": self.title,
            "series_title": self.series_title,
            "section_title": self.section_title,
            "part_title": self.part_title,
            "collection_title": self.collection_title,
            "interact_title": self.interact_title,
            "parent_title": self.parent_title,

            "duration": self.duration,

            "download_base_path": self.download_base_path,
            "download_path": self.download_path,
            "file_name": self.file_name,
            "progress": self.progress,
            "total_file_size": self.total_file_size,
            "total_downloaded_size": self.total_downloaded_size,
            "current_downloaded_size": self.current_downloaded_size,
            "status": self.status,

            "video_quality_id": self.video_quality_id,
            "audio_quality_id": self.audio_quality_id,
            "video_codec_id": self.video_codec_id,
            "video_type": self.video_type,
            "audio_type": self.audio_type,
            "output_type": self.output_type,

            "download_items": self.download_items,
            
            "parse_type": self.parse_type,
            "download_type": self.download_type,
            "stream_type": self.stream_type,
            "download_option": self.download_option,
            "ffmpeg_merge": self.ffmpeg_merge,
            "further_processing": self.further_processing,
            "flv_video_count": self.flv_video_count,

            "extra_option": self.extra_option,

            "pubtimestamp": self.pubtimestamp,
            "area": self.area,
            "zone": self.zone,
            "subzone": self.subzone,
            "up_name": self.up_name,
            "up_uid": self.up_uid,
            "badge": self.badge,
            "season_num": self.season_num,
            "episode_num": self.episode_num,
            "bangumi_type": self.bangumi_type,
            "template_type": self.template_type,
            "template": self.template,
            "total_count": self.total_count,

            "video_width": self.video_width,
            "video_height": self.video_height,

            "source": self.source,

            "thread_info": self.thread_info,
            "error_info": self.error_info
        }

    def load_from_dict(self, data: dict):
        self.min_version = data.get("min_version", self.min_version)

        self.id = data.get("id", self.id)
        self.number = data.get("number", self.number)
        self.zero_padding_number = data.get("zero_padding_number", self.zero_padding_number)
        self.list_number = data.get("list_number", self.list_number)
        self.timestamp = data.get("timestamp", self.timestamp)
        self.page = data.get("page", self.page)

        self.referer_url = data.get("referer_url", self.referer_url)
        self.cover_url = data.get("cover_url", self.cover_url)

        self.bvid = data.get("bvid", self.bvid)
        self.cid = data.get("cid", self.cid)
        self.aid = data.get("aid", self.aid)
        self.ep_id = data.get("ep_id", self.ep_id)
        self.season_id = data.get("season_id", self.season_id)
        self.media_id = data.get("media_id", self.media_id)

        self.title = data.get("title", self.title)
        self.series_title = data.get("series_title", self.series_title)
        self.section_title = data.get("section_title", self.section_title)
        self.part_title = data.get("part_title", self.part_title)
        self.collection_title = data.get("collection_title", self.collection_title)
        self.interact_title = data.get("interact_title", self.interact_title)
        self.parent_title = data.get("parent_title", self.parent_title)

        self.duration = data.get("duration", self.duration)

        self.download_base_path = data.get("download_base_path", self.download_base_path)
        self.download_path = data.get("download_path", self.download_path)
        self.file_name = data.get("file_name", self.file_name)
        self.progress = data.get("progress", self.progress)
        self.total_file_size = data.get("total_file_size", self.total_file_size)
        self.total_downloaded_size = data.get("total_downloaded_size", self.total_downloaded_size)
        self.current_downloaded_size = data.get("current_downloaded_size", self.current_downloaded_size)
        self.status = data.get("status", self.status)

        self.video_quality_id = data.get("video_quality_id", self.video_quality_id)
        self.audio_quality_id = data.get("audio_quality_id", self.audio_quality_id)
        self.video_codec_id = data.get("video_codec_id", self.video_codec_id)
        self.video_type = data.get("video_type", self.video_type)
        self.audio_type = data.get("audio_type", self.audio_type)
        self.output_type = data.get("output_type", self.output_type)

        self.download_items = data.get("download_items", self.download_items)

        self.parse_type = data.get("parse_type", self.parse_type)
        self.download_type = data.get("download_type", self.download_type)
        self.stream_type = data.get("stream_type", self.stream_type)
        self.download_option = data.get("download_option", self.download_option)
        self.ffmpeg_merge = data.get("ffmpeg_merge", self.ffmpeg_merge)
        self.further_processing = data.get("further_processing", self.further_processing)
        self.flv_video_count = data.get("flv_video_count", self.flv_video_count)

        self.extra_option = data.get("extra_option", self.extra_option)
        
        self.pubtimestamp = data.get("pubtimestamp", self.pubtimestamp)
        self.area = data.get("area", self.area)
        self.zone = data.get("zone", self.zone)
        self.subzone = data.get("subzone", self.subzone)
        self.up_name = data.get("up_name", self.up_name)
        self.up_uid = data.get("up_uid", self.up_uid)
        self.badge = data.get("badge", self.badge)
        self.season_num = data.get("season_num", self.season_num)
        self.episode_num = data.get("episode_num", self.episode_num)
        self.bangumi_type = data.get("bangumi_type", self.bangumi_type)
        self.template_type = data.get("template_type", self.template_type)
        self.template = data.get("template", self.template)
        self.total_count = data.get("total_count", self.total_count)

        self.video_width = data.get("video_width", self.video_width)
        self.video_height = data.get("video_height", self.video_height)

        self.source = data.get("source", self.source)

        self.thread_info = data.get("thread_info", self.thread_info)
        self.error_info = data.get("error_info", self.error_info)

    def load_from_file(self, file_path: str):
        with open(file_path, "r", encoding = "utf-8") as f:
            data = json.loads(f.read())

            self.load_from_dict(data)

    def update(self):
        self.min_version = Config.APP.task_file_min_version_code

        self.write(self.to_dict())

    def remove_file(self):
        File.remove_file(self.file_path)

    def write(self, contents: dict):
        with open(self.file_path, "w", encoding = "utf-8") as f:
            f.write(json.dumps(contents, ensure_ascii = False, indent = 4))

    def is_valid(self):
        return self.min_version >= Config.APP.task_file_min_version_code

    @property
    def file_path(self):
        return os.path.join(Config.User.download_file_directory, f"info_{self.id}.json")