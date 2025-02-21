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

        # 视频原标题
        self.title: str = ""

        # 视频时长
        self.duration: int = 0

        # 下载信息
        self.progress: int = 0
        # 总大小，单位字节
        self.total_size: int = 0
        # 已下载完成的总大小，单位字节
        self.completed_size: int = 0
        # 已下载完成的当前任务大小
        self.current_completed_size: int = 0
        # 下载状态
        self.status: int = DownloadStatus.Waiting.value

        # 媒体信息，0 表示未定义
        self.video_quality_id: int = 0
        self.audio_quality_id: int = 0
        self.video_codec_id: int = 0
        self.audio_type: str = ""

        # 下载项目标识
        self.item_flag: list = None

        # 下载类型，1 为投稿视频，2 为番组
        self.download_type: int = 0
        # 视频流类型
        self.stream_type: int = 0
        # 视频合成类型
        self.video_merge_type: int = 0
        # 视频个数，仅 flv 有效
        self.video_count: int = 0

        # 附加内容选项
        self.get_danmaku: bool = False
        self.danmaku_type: int = 0
        self.get_cover: bool = False
        self.get_subtitle: bool = False
        self.subtitle_type: int = 0

    def to_dict(self):
        return {
            "id": self.id,
            "index": self.index,
            "index_with_zero": self.index_with_zero,
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
            "total_size": self.total_size,
            "completed_size": self.completed_size,
            "current_completed_size": self.current_completed_size,
            "status": self.status,
            "video_quality_id": self.video_quality_id,
            "audio_quality_id": self.audio_quality_id,
            "video_codec_id": self.video_codec_id,
            "audio_type": self.audio_type,
            "item_flag": self.item_flag,
            "download_type": self.download_type,
            "stream_type": self.stream_type,
            "video_merge_type": self.video_merge_type,
            "video_count": self.video_count,
            "get_danmaku": self.get_danmaku,
            "danmaku_type": self.danmaku_type,
            "get_cover": self.get_cover,
            "get_subtitle": self.get_subtitle,
            "subtitle_type": self.subtitle_type
        }

    def load_from_dict(self, data: Dict):
        self.id = data["id"]
        self.index = data["index"]
        self.index_with_zero = data["index_with_zero"]
        self.timestamp = data["timestamp"]
        self.referer_url = data["referer_url"]
        self.cover_url = data["cover_url"]
        self.bvid = data["bvid"]
        self.cid = data["cid"]
        self.aid = data["aid"]
        self.ep_id = data["ep_id"]
        self.title = data["title"]
        self.duration = data["duration"]
        self.progress = data["progress"]
        self.total_size = data["total_size"]
        self.completed_size = data["completed_size"]
        self.current_completed_size = data["current_completed_size"]
        self.status = data["status"]
        self.video_quality_id = data["video_quality_id"]
        self.audio_quality_id = data["audio_quality_id"]
        self.video_codec_id = data["video_codec_id"]
        self.audio_type = data["audio_type"]
        self.item_flag = data["item_flag"]
        self.download_type = data["download_type"]
        self.video_merge_type = data["video_merge_type"]
        self.video_count = data["video_count"]
        self.stream_type = data["stream_type"]
        self.get_danmaku = data["get_danmaku"]
        self.danmaku_type = data["danmaku_type"]
        self.get_cover = data["get_cover"]
        self.get_subtitle = data["get_subtitle"]
        self.subtitle_type = data["subtitle_type"]

class ThreadInfo:
    # 线程信息
    def __init__(self):
        # 文件名称
        self.file_name: str = ""
        # range 分片信息
        self.range: List[int] = []

    def to_dict(self):
        return {
            "file_name": self.file_name,
            "range": self.range
        }
    
    def load_from_dict(self, data: Dict):
        self.file_name = data["file_name"]
        self.range = data["range"]

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
        self.url_list = data["url_list"]
        self.type = data["type"]
        self.file_name = data["file_name"]

class RangeDownloadInfo:
    def __init__(self):
        self.index: str = ""
        self.type: str = ""
        self.url: str = ""
        self.referer_url: str = ""
        self.file_path: str = ""
        self.range: List[int] = []

class DownloaderCallback:
    def __init__(self):
        self.onStartCallback: Callable = None
        self.onDownloadCallback: Callable = None
        self.onMergeCallback: Callable = None
        self.onErrorCallback: Callable = None

class UtilsCallback:
    def __init__(self):
        self.onMergeFinishCallback: Callable = None
        self.onMergeFailedCallback: Callable = None
        self.onDownloadFailedCallback: Callable = None

class TaskPanelCallback:
    def __init__(self):
        self.onStartNextCallback: Callable = None
        self.onStopCallbacak: Callable = None
        self.onUpdateTaskCountCallback: Callable = None
        self.onLoadMoreTaskCallback: Callable = None

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
