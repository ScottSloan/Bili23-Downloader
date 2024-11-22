from typing import Callable, List, Dict

class DownloadTaskInfo:
    # 下载任务信息
    def __init__(self):
        from utils.config import Config

        # id，区分不同下载任务的唯一标识符
        self.id: int = 0
        # 序号，从 1 开始，0 为空
        self.index: int = 0
        
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

        # 下载信息
        self.progress: int = 0
        # 总大小，单位字节
        self.total_size: int = 0
        # 已下载完成的大小，单位字节
        self.completed_size: int = 0
        # 下载状态
        self.status: int = Config.Type.DOWNLOAD_STATUS_WAITING
        # 下载完成标识符
        self.download_finish_flag: bool = False

        # 媒体信息，0 表示未定义
        self.video_quality_id: int = Config.Type.UNDEFINED
        self.audio_quality_id: int = Config.Type.UNDEFINED
        self.video_codec_id: int = Config.Type.UNDEFINED
        self.audio_type: str = ""

        # 下载类型，1 为用户投稿视频，2 为番组
        self.download_type: int = Config.Type.UNDEFINED
        # 视频合成类型
        self.video_merge_type: int = 0

        # 回调函数指针
        self.startDwonload_Callback: Callable = None
        self.onPause_Callback: Callable = None
        self.onResume_Callback: Callable = None
        self.onStop_Callback: Callable = None

    def to_dict(self):
        return {
            "id": self.id,
            "index": self.index,
            "referer_url": self.referer_url,
            "cover_url": self.cover_url,
            "bvid": self.bvid,
            "cid": self.cid,
            "title": self.title,
            "title_legal": self.title_legal,
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
            "download_finish_flag": self.download_finish_flag
        }

    def load_from_dict(self, data: Dict):
        self.id = data["id"]
        self.index = data["index"]
        self.referer_url = data["referer_url"]
        self.cover_url = data["cover_url"]
        self.bvid = data["bvid"]
        self.cid = data["cid"]
        self.title = data["title"]
        self.title_legal = data["title_legal"]
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
        self.download_finish_flag = data["download_finish_flag"]

class ThreadInfo:
    # 线程信息
    def __init__(self):
        # 文件名称
        self.file_name: str = ""
        # 下载类型，0为视频，1为音频
        self.download_type: int = 0
        # range 分片信息
        self.range: List[int] = []

    def to_dict(self):
        return {
            "file_name": self.file_name,
            "thread_type": self.download_type,
            "range": self.range
        }
    
    def load_from_dict(self, data: Dict):
        self.file_name = data["file_name"]
        self.download_type = data["download_type"]
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
        self.index: int = 0
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
        self.onErrorCallback: Callable = None

class TaskPanelCallback:
    def __init__(self):
        self.onStartNextCallback: Callable = None
        self.onStopCallbacak: Callable = None
        self.onUpdateTaskCountCallback: Callable = None
