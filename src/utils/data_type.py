from typing import Callable, List, Dict

class DownloadTaskInfo:
    # 下载任务信息
    def __init__(self):
        from utils.config import Config

        # id，区分不同下载任务的唯一标识符
        self.id: int = 0
        # 序号，从 1 开始，0 为空
        self.index: int = 0
        # 时间戳
        self.timestamp: int = 0
        
        # Referer URL
        self.referer_url: str = ""
        # 视频封面链接
        self.cover_url = ""

        # 视频 bvid 和 cid 信息
        self.bvid: str = ""
        self.cid: int = ""

        # 视频原标题
        self.title: str = ""
        # 去除特殊符号的视频标题，可作为文件名
        self.title_legal: str = ""

        # 视频时长
        self.duration: int = 0

        # 下载信息
        self.progress: int = 0
        # 总大小，单位字节
        self.total_size: int = 0
        # 已下载完成的大小，单位字节
        self.completed_size: int = 0
        # 下载状态
        self.status: int = Config.Type.DOWNLOAD_STATUS_WAITING

        # 媒体信息，0 表示未定义
        self.video_quality_id: int = Config.Type.UNDEFINED
        self.audio_quality_id: int = Config.Type.UNDEFINED
        self.video_codec_id: int = Config.Type.UNDEFINED
        self.audio_type: str = ""

        # 下载类型，1 为用户投稿视频，2 为番组
        self.download_type: int = Config.Type.UNDEFINED
        # 视频合成类型
        self.video_merge_type: int = 0

        # 附加内容选项
        self.get_danmaku: bool = False
        self.danmaku_type: int = 0
        self.get_cover: bool = False

    def to_dict(self):
        return {
            "id": self.id,
            "index": self.index,
            "timestamp": self.timestamp,
            "referer_url": self.referer_url,
            "cover_url": self.cover_url,
            "bvid": self.bvid,
            "cid": self.cid,
            "title": self.title,
            "title_legal": self.title_legal,
            "duration": self.duration,
            "progress": self.progress,
            "total_size": self.total_size,
            "completed_size": self.completed_size,
            "status": self.status,
            "video_quality_id": self.video_quality_id,
            "audio_quality_id": self.audio_quality_id,
            "video_codec_id": self.video_codec_id,
            "audio_type": self.audio_type,
            "download_type": self.download_type,
            "video_merge_type": self.video_merge_type,
            "get_danmaku": self.get_danmaku,
            "danmaku_type": self.danmaku_type,
            "get_cover": self.get_cover
        }

    def load_from_dict(self, data: Dict):
        self.id = data["id"]
        self.index = data["index"]
        self.timestamp = data["timestamp"]
        self.referer_url = data["referer_url"]
        self.cover_url = data["cover_url"]
        self.bvid = data["bvid"]
        self.cid = data["cid"]
        self.title = data["title"]
        self.title_legal = data["title_legal"]
        self.duration = data["duration"]
        self.progress = data["progress"]
        self.total_size = data["total_size"]
        self.completed_size = data["completed_size"]
        self.status = data["status"]
        self.video_quality_id = data["video_quality_id"]
        self.audio_quality_id = data["audio_quality_id"]
        self.video_codec_id = data["video_codec_id"]
        self.audio_type = data["audio_type"]
        self.download_type = data["download_type"]
        self.video_merge_type = data["video_merge_type"]
        self.get_danmaku = data["get_danmaku"]
        self.danmaku_type = data["danmaku_type"]
        self.get_cover = data["get_cover"]

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

class ErrorLog:
    def __init__(self):
        self.log: str = ""
        self.time: str = ""
        self.return_code: int = 0

class NotificationMessage:
    def __init__(self):
        self.video_title: str = ""
        self.status: int = 0
        self.video_merge_type: int = 0
