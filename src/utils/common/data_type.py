from abc import ABC, abstractmethod
from typing import List, Dict

from utils.common.enums import DownloadStatus

class DownloadTaskInfo:
    def __init__(self):
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
        self.list_title: str = ""

        # 视频时长
        self.duration: int = 0

        # 下载信息
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

        # 下载类型
        self.download_type: int = 0
        # 视频流类型
        self.stream_type: int = 0
        # 下载选项
        self.download_option: List[int] = []
        # 是否调用 FFmpeg 合并
        self.ffmpeg_merge: bool = False
        # flv 视频个数，仅 flv 流时有效
        self.flv_video_count: int = 0

        # 附加内容选项
        self.extra_option: dict = {}

        # 视频发布时间戳
        self.pubtime: int = 0
        # 地区
        self.area: str = ""
        # 分区信息
        self.zone_info: dict = {}
        # UP 主信息
        self.up_info: dict = {}

    def to_dict(self):
        return {
            "id": self.id,
            "number": self.number,
            "zero_padding_number": self.zero_padding_number,
            "list_number": self.list_number,
            "timestamp": self.timestamp,

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
            "list_title": self.list_title,

            "duration": self.duration,

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
            
            "download_type": self.download_type,
            "stream_type": self.stream_type,
            "download_option": self.download_option,
            "ffmpeg_merge": self.ffmpeg_merge,
            "flv_video_count": self.flv_video_count,

            "extra_option": self.extra_option,

            "pubtime": self.pubtime,
            "area": self.area,
            "zone_info": self.zone_info,
            "up_info": self.up_info,
        }

    def load_from_dict(self, data: Dict):
        self.id = data.get("id", self.id)
        self.number = data.get("number", self.number)
        self.zero_padding_number = data.get("zero_padding_number", self.zero_padding_number)
        self.list_number = data.get("list_number", self.list_number)
        self.timestamp = data.get("timestamp", self.timestamp)

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
        self.list_title = data.get("list_title", self.list_title)

        self.duration = data.get("duration", self.duration)

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

        self.download_type = data.get("download_type", self.download_type)
        self.stream_type = data.get("stream_type", self.stream_type)
        self.download_option = data.get("download_option", self.download_option)
        self.ffmpeg_merge = data.get("ffmpeg_merge", self.ffmpeg_merge)
        self.flv_video_count = data.get("flv_video_count", self.flv_video_count)

        self.extra_option = data.get("extra_option", self.extra_option)
        
        self.pubtime = data.get("pubtime", self.pubtime)
        self.area = data.get("area", self.area)
        self.zone_info = data.get("zone_info", self.zone_info)
        self.up_info = data.get("up_info", self.up_info)

class DownloaderInfo:
    def __init__(self):
        self.url_list: List[str] = []
        self.type: str = ""
        self.file_name: str = ""

    def to_dict(self):
        return {
            "url_list": self.url_list,
            "type": self.type,
            "file_name": self.file_name
        }
    
    def load_from_dict(self, data: Dict):
        self.url_list = data.get("url_list")
        self.type = data.get("type")
        self.file_name = data.get("file_name")

class RangeDownloadInfo:
    index: str = ""
    type: str = ""
    url: str = ""
    file_path: str = ""
    range: List[int] = []

class DownloaderCallback(ABC):
    @staticmethod
    @abstractmethod
    def onStart():
        pass
    
    @staticmethod
    @abstractmethod
    def onDownloading(speed: str):
        pass
    
    @staticmethod
    @abstractmethod
    def onComplete():
        pass
    
    @staticmethod
    @abstractmethod
    def onError():
        pass

class TaskPanelCallback(ABC):
    @staticmethod
    @abstractmethod
    def onStartNextTask():
        pass
    
    @staticmethod
    @abstractmethod
    def onUpdateCountTitle(show_toast = False):
        pass
    
    @staticmethod
    @abstractmethod
    def onAddPanel(task_info: DownloadTaskInfo):
        pass

class DownloadPageCallback(ABC):
    @staticmethod
    @abstractmethod
    def onSetTitle(name: str, count: int):
        pass
    
    @staticmethod
    @abstractmethod
    def onAddPanel(task_info: DownloadTaskInfo):
        pass
    
    @staticmethod
    @abstractmethod
    def onStartNextTask():
        pass

class NotificationMessage:
    def __init__(self):
        self.video_title: str = ""
        self.status: int = 0
        self.video_merge_type: int = 0

class TreeListCallback(ABC):
    @staticmethod
    @abstractmethod
    def onUpdateCheckedItemCount(count: int):
        pass

class TreeListItemInfo:
    def __init__(self):
        self.number: int = 0
        self.page: int = 0

        self.title: str = ""

        self.cid: int = 0
        self.aid: int = 0
        self.bvid: str = ""
        self.ep_id: int = 0
        self.season_id: int = 0
        self.media_id: int = 0

        self.pubtime: int = 0
        self.badge: str = ""
        self.duration: str = ""
        self.cover_url: str = ""

        self.pid: str = ""

        self.section_title: str = ""
        self.part_title: str = ""
        self.list_title: str = ""

        self.room_id: int = 0

        self.item_type: str = "node"
        self.type: str = 0

    def to_dict(self):
        return {
            "number": self.number,
            "page": self.page,
            "title": self.title,
            "cid": self.cid,
            "aid": self.aid,
            "bvid": self.bvid,
            "ep_id": self.ep_id,
            "season_id": self.season_id,
            "media_id": self.media_id,
            "pubtime": self.pubtime,
            "badge": self.badge,
            "duration": self.duration,
            "cover_url": self.cover_url,
            "pid": self.pid,
            "section_title": self.section_title,
            "part_title": self.part_title,
            "list_title": self.list_title,
            "room_id": self.room_id,
            "item_type": self.item_type,
            "type": self.type
        }

    def load_from_dict(self, data: dict):
        self.number = data.get("number", self.number)
        self.page = data.get("page", self.page)
        self.title = data.get("title", self.title)
        self.cid = data.get("cid", self.cid)
        self.aid = data.get("aid", self.aid)
        self.bvid = data.get("bvid", self.bvid)
        self.ep_id = data.get("ep_id", self.ep_id)
        self.season_id = data.get("season_id", self.season_id)
        self.media_id = data.get("media_id", self.media_id)
        self.pubtime = data.get("pubtime", self.pubtime)
        self.badge = data.get("badge", self.badge)
        self.duration = data.get("duration", self.duration)
        self.cover_url = data.get("cover_url", self.cover_url)
        self.pid = data.get("pid", self.pid)
        self.section_title = data.get("section_title", self.section_title)
        self.part_title = data.get("part_title", self.part_title)
        self.list_title = data.get("list_title", self.list_title)
        self.room_id = data.get("room_id", self.room_id)
        self.item_type = data.get("item_type", self.item_type)
        self.type = data.get("type", self.type)

class Command:
    def __init__(self):
        self.command = []

    def add(self, command: str):
        self.command.append(command)

    def clear(self):
        self.command.clear()

    def format(self):
        return " && ".join(self.command)

class Process:
    output: str = None
    return_code: int = None

class Callback(ABC):
    @staticmethod
    @abstractmethod
    def onSuccess(*args, **kwargs):
        pass
    
    @staticmethod
    @abstractmethod
    def onError(*args, **kwargs):
        pass

class ParseCallback(ABC):
    @staticmethod
    @abstractmethod
    def onError():
        pass
    
    @staticmethod
    @abstractmethod
    def onBangumi(url: str):
        pass
    
    @staticmethod
    @abstractmethod
    def onInteractVideo():
        pass
    
    @staticmethod
    @abstractmethod
    def onUpdateInteractVideo(title: str):
        pass