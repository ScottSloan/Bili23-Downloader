from typing import Callable, List, Dict

from utils.common.enums import DownloadStatus

class DownloadTaskInfo:
    # 下载任务信息
    def __init__(self):
        # id，区分不同下载任务的唯一标识符
        self.id: int = None
        # 序号，从 1 开始
        self.number: int = 0
        # 补零序号
        self.number_with_zero: str = ""
        # 列表中的序号
        self.list_number: int = 0
        # 后缀
        self.suffix: str = ""
        # 时间戳
        self.timestamp: int = 0
        
        # Referer URL
        self.referer_url: str = None
        # 视频封面链接
        self.cover_url: str = None

        # 视频 bvid 和 cid 信息
        self.bvid: str = None
        self.cid: int = None
        self.aid: int = None
        self.ep_id: int = None

        # 视频标题
        self.title: str = None
        # 剧集名称
        self.series: str = None

        # 视频时长
        self.duration: int = None

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
        self.video_quality_id: int = None
        self.audio_quality_id: int = None
        self.video_codec_id: int = None
        self.video_type: str = None
        self.audio_type: str = None
        self.output_type: str = ""

        # 下载项目标识
        self.download_items: list = []

        # 下载类型
        self.download_type: int = 0
        # 视频流类型
        self.stream_type: int = None
        # 下载选项
        self.download_option: List[int] = []
        # 是否调用 FFmpeg 合并
        self.ffmpeg_merge: bool = False
        # flv 视频个数，仅 flv 流时有效
        self.flv_video_count: int = None

        # 附加内容选项
        self.extra_option: dict = None

        # 视频发布时间戳
        self.pubtime: int = 0
        # 地区
        self.area: str = ""
        # 分区信息
        self.tname_info: dict = {}
        # UP 主信息
        self.up_info: dict = {}

    def to_dict(self):
        return {
            "id": self.id,
            "number": self.number,
            "number_with_zero": self.number_with_zero,
            "list_number": self.list_number,
            "suffix": self.suffix,
            "timestamp": self.timestamp,
            "referer_url": self.referer_url,
            "cover_url": self.cover_url,
            "bvid": self.bvid,
            "cid": self.cid,
            "aid": self.aid,
            "ep_id": self.ep_id,
            "title": self.title,
            "series": self.series,
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
            "tname_info": self.tname_info,
            "up_info": self.up_info,
        }

    def load_from_dict(self, data: Dict):
        self.id = data.get("id")
        self.number = data.get("number")
        self.number_with_zero = data.get("number_with_zero")
        self.list_number = data.get("list_number")
        self.suffix = data.get("suffix")
        self.timestamp = data.get("timestamp")
        self.referer_url = data.get("referer_url")
        self.cover_url = data.get("cover_url")
        self.bvid = data.get("bvid")
        self.cid = data.get("cid")
        self.aid = data.get("aid")
        self.ep_id = data.get("ep_id")
        self.title = data.get("title")
        self.series = data.get("series")
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
        self.pubtime = data.get("pubtime")
        self.area = data.get("area")
        self.tname_info = data.get("tname_info")
        self.up_info = data.get("up_info")

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
    def onStart():
        pass

    def onDownloading(speed: str):
        pass

    def onComplete():
        pass

    def onError():
        pass

class TaskPanelCallback:
    def onStartNextTask():
        pass

    def onUpdateCountTitle(show_toast = False):
        pass

    def onAddPanel(task_info: DownloadTaskInfo):
        pass

class DownloadPageCallback:
    def onSetTitle(name: str, count: int):
        pass

    def onAddPanel(task_info: DownloadTaskInfo):
        pass

    def onStartNextTask():
        pass

class NotificationMessage:
    def __init__(self):
        self.video_title: str = ""
        self.status: int = 0
        self.video_merge_type: int = 0

class TreeListItemInfo:
    def __init__(self):
        self.list_number: int = 0
        self.type: str = ""
        self.title: str = ""
        self.cid: int = 0

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

class Callback:
    def onSuccess(*args, **kwargs):
        pass
    
    def onError(*args, **kwargs):
        pass

class ParseCallback:
    def onError():
        pass

    def onBangumi(url: str):
        pass

    def onInteractVideo():
        pass

    def onUpdateInteractVideo(title: str):
        pass

class MergeCallback:
    def onSuccess(*args, **kwargs):
        pass

    def onError(*args, **kwargs):
        pass

    def onUpdateSuffix():
        pass
