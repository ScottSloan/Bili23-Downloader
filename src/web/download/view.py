"""
TaskInfo → 给前端看的形状（S3-9）

**快照与增量事件必须用同一个函数序列化。** 两边各写一份的话，字段迟早对不齐，
而症状是「刷新前后同一个任务显示得不一样」—— 这种 bug 看起来像随机现象。

只挑前端真正要用的字段：TaskInfo 里还有分片断点、aria2 的 gid、cookie 相关的东西，
既没用又不该发出去。
"""

from typing import List
import logging

from util.common.enum import DownloadStatus, DownloadType
from util.download.task.info import TaskInfo

logger = logging.getLogger(__name__)

def status_name(status: int) -> str:
    """
    状态转成小写字符串

    不直接发数字：前端拿到 `6` 得回头查枚举，而且这些数字一旦调整，
    两端就得同时改。发名字则是自解释的
    """
    try:
        return DownloadStatus(status).name.lower()

    except ValueError:
        return "unknown"

def type_flags(download_type: int) -> List[str]:
    """把 DownloadType 位掩码摊成名字列表"""
    return [flag.name.lower() for flag in DownloadType if download_type & flag != 0]

def task_view(task_info: TaskInfo) -> dict:
    return {
        "task_id": task_info.Basic.task_id,
        "title": task_info.Basic.show_title,
        "cover_id": task_info.Basic.cover_id,
        # 封面**给地址不给图**：桌面版把它下载成 QPixmap 存进 thumbnail.db，
        # 而 QPixmap 交不给浏览器。这边直接让浏览器去 B 站图床取，
        # 页面本来就带 referrer=no-referrer，不会因为缺 Referer 被拒
        "cover": task_info.Episode.cover,
        "created_time": task_info.Basic.created_time,
        "completed_time": task_info.Basic.completed_time,

        "status": status_name(task_info.Download.status),
        "status_label": task_info.Download.status_label,
        "info_label": task_info.Download.info_label,

        "progress": task_info.Download.progress,
        "speed": task_info.Download.speed,
        "total_size": task_info.Download.total_size,
        "downloaded_size": task_info.Download.downloaded_size,

        "type": type_flags(task_info.Download.type),

        "file_name": task_info.File.name,
        "download_path": task_info.File.download_path,
        "folder": task_info.File.folder,

        # 这三个是**已经拼成文案**的（供文件命名规则用）。服务端进程里没有 Qt 的
        # 翻译函数，它们一律是英文，界面上别直接显示 —— 前端按下面那三个 id
        # 查自己的译文（D12）
        "video_quality": task_info.Episode.video_quality,
        "audio_quality": task_info.Episode.audio_quality,
        "video_codec": task_info.Episode.video_codec,

        "video_quality_id": task_info.Download.video_quality_id,
        "audio_quality_id": task_info.Download.audio_quality_id,
        "video_codec_id": task_info.Download.video_codec_id,
        "duration": task_info.Episode.duration,
        "url": task_info.Episode.url,
    }

def task_views(task_list: List[TaskInfo]) -> List[dict]:
    views = []

    for task_info in task_list:
        try:
            views.append(task_view(task_info))

        except Exception:
            # 单个任务的记录坏掉（旧版本遗留的字段缺失等）不该让整份快照取不出来
            logger.exception("序列化任务失败：%s", getattr(task_info.Basic, "task_id", "?"))

    return views
