from typing import Callable, List, Dict

from utils.common.enums import DownloadStatus

class DownloadTaskInfo:
    # 下载任务信息
    def __init__(self):
        # id，区分不同下载任务的唯一标识符
        self.id: int = 0
        # 序号，从 1 开始，0 为空
        self.index: int = 0
        # 补零序号
        self.index_with_zero: str = ""
        # 后缀
        self.suffix: str = ""
        # 时间戳
        self.timestamp: int = 0
        
        # Referer URL
        self.referer_url: str = ""
        # 视频封面链接
        self.cover_url = ""

        # 视频 bvid 和 cid 信息
        self.bvid: str = ""
        self.cid: int = 0
        self.aid: int = 0
        self.ep_id: int = 0

        # 视频标题
        self.title: str = ""

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
        self.audio_quality_id: int = 0
        self.video_codec_id: int = 0
        self.video_type: str = None
        self.audio_type: str = None
        self.output_type: str = None

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

    def to_dict(self):
        return {
            "id": self.id,
            "index": self.index,
            "index_with_zero": self.index_with_zero,
            "suffix": self.suffix,
            "timestamp": self.timestamp,
            "referer_url": self.referer_url,
            "cover_url": self.cover_url,
            "bvid": self.bvid,
            "cid": self.cid,
            "aid": self.aid,
            "ep_id": self.ep_id,
            "title": self.title,
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
            "extra_option": self.extra_option
        }

    def load_from_dict(self, data: Dict):
        self.id = data.get("id")
        self.index = data.get("index")
        self.index_with_zero = data.get("index_with_zero")
        self.suffix = data.get("suffix")
        self.timestamp = data.get("timestamp")
        self.referer_url = data.get("referer_url")
        self.cover_url = data.get("cover_url")
        self.bvid = data.get("bvid")
        self.cid = data.get("cid")
        self.aid = data.get("aid")
        self.ep_id = data.get("ep_id")
        self.title = data.get("title")
        self.duration = data.get("duration")
        self.progress = data.get("progress")
        self.total_file_size = data.get("total_file_size")
        self.total_downloaded_size = data.get("total_downloaded_size")
        self.current_downloaded_size = data.get("current_downloaded_size")
        self.status = data.get("status")
        self.video_quality_id = data.get("video_quality_id")
        self.audio_quality_id = data.get("audio_quality_id")
        self.video_codec_id = data.get("video_codec_id")
        self.video_type = data.get("video_type")
        self.audio_type = data.get("audio_type")
        self.output_type = data.get("output_type")
        self.download_items = data.get("download_items")
        self.download_type = data.get("download_type")
        self.stream_type = data.get("stream_type")
        self.download_option = data.get("download_option")
        self.ffmpeg_merge = data.get("ffmpeg_merge")
        self.flv_video_count = data.get("flv_video_count")
        self.extra_option = data.get("extra_option")

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
    def __init__(self):
        self.index: str = ""
        self.type: str = ""
        self.url: str = ""
        self.file_path: str = ""
        self.range: List[int] = []

class DownloaderCallback:
    def __init__(self):
        self.onStartDownloadCallback: Callable = None
        self.onDownloadingCallback: Callable = None
        self.onDownloadFinish: Callable = None
        self.onErrorCallback: Callable = None

class TaskPanelCallback:
    def __init__(self):
        self.onStartNextCallback: Callable = None
        self.onUpdateCountTitleCallback: Callable = None
        self.onLoadMoreTaskCallback: Callable = None
        self.onAddPanelCallback: Callable = None

class DownloadPageCallback:
    def __init__(self):
        self.onSetTitleCallback: Callable = None
        self.onAddPanelCallback: Callable = None
        self.onStartNextCallback: Callable = None

class NotificationMessage:
    def __init__(self):
        self.video_title: str = ""
        self.status: int = 0
        self.video_merge_type: int = 0

class TreeListItemInfo:
    def __init__(self):
        self.type: str = ""
        self.title: str = ""
        self.cid: int = 0

class ExceptionInfo:
    def __init__(self):
        self.timestamp: str = ""
        self.source: str = ""
        self.id: str = ""
        self.return_code: str = ""
        self.exception_type: str = ""
        self.log: str = ""
        self.short_log: str = ""
    
    def to_dict(self):
        return {
            "timestamp": self.timestamp,
            "source": self.source,
            "id": self.id,
            "return_code": self.return_code,
            "exception_type": self.exception_type,
            "log": self.log,
            "short_log": self.short_log
        }
    
    def from_dict(self, data: dict):
        self.timestamp = data.get("timestamp")
        self.source = data.get("source")
        self.id = data.get("id")
        self.return_code = data.get("return_code")
        self.exception_type = data.get("exception_type")
        self.log = data.get("log")
        self.short_log = data.get("short_log")

class ParseCallback:
    def __init__(self):
        self.error_callback: Callable = None
        self.redirect_callback: Callable = None

class Command:
    def __init__(self):
        self.command = []

    def add(self, command):
        self.command.append(command)

    def clear(self):
        self.command.clear()

    def format(self):
        return " && ".join(self.command)

class MergeCallback:
    def __init__(self):
        self.onSuccess = None
        self.onError = None

class ExtraOption:
    def __init__(self):
        self.download_danmaku_file: bool = False
        self.danmaku_file_type: int = 0

        self.download_subtitle_file: bool = False
        self.subtitle_file_type: int = 0

        self.download_cover_file: bool = False
    
    def load_from_dict(self, data: dict):
        self.download_danmaku_file = data.get("download_danmaku_file", self.download_danmaku_file)
        self.danmaku_file_type = data.get("danmaku_file_type", self.danmaku_file_type)
        self.download_subtitle_file = data.get("download_subtitle_file", self.download_subtitle_file)
        self.subtitle_file_type = data.get("subtitle_file_type", self.subtitle_file_type)
        self.download_cover_file = data.get("download_cover_file", self.download_cover_file)