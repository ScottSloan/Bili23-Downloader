from typing import Callable, Optional

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
        self.status: str = "wait"
        # 下载完成标识符
        self.download_finish_flag = False

        # 媒体信息，0 表示未定义
        self.video_quality_id = Config.Type.UNDEFINED
        self.audio_quality_id = Config.Type.UNDEFINED
        self.video_codec = Config.Type.UNDEFINED

        # 下载类型，1 为用户投稿视频，2 为番组
        self.download_type: int = Config.Type.UNDEFINED
        # 视频合成类型
        self.video_merge_type: int = 0

        # 回调函数指针
        self.startDwonload_Callback: Optional[Callable] = None
        self.onPause_Callback: Optional[Callable] = None
        self.onResume_Callback: Optional[Callable] = None
        self.onStop_Callback: Optional[Callable] = None

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
            "video_quality": self.video_quality_id,
            "audio_quality": self.audio_quality_id,
            "video_codec": self.video_codec,
            "download_type": self.download_type,
            "video_merge_type": self.video_merge_type,
            "download_finish_flag": self.download_finish_flag
        }

    def load_from_dict(self, data):
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
        self.video_quality_id = data["video_quality"]
        self.video_codec = data["video_codec"]
        self.download_type = data["download_type"]
        self.video_merge_type = data["video_merge_type"]
        self.download_finish_flag = data["download_finish_flag"]