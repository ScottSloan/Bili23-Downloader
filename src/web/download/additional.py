"""
附加内容（弹幕 / 字幕 / 封面 / 章节 / 元数据）—— 走 httpx，不进 aria2（S3-6 / D4）

**为什么不交给 aria2**：这些是几十 KB 的小文件，多数还不是「下载」而是「取回来再转换」——
弹幕要从 protobuf 转成 XML / ASS / JSON，元数据要拼成 NFO，章节要生成 FFmpeg 的章节文件。
交给 aria2 只能省下取字节那一步，却要为它们各自维护一份 gid、状态与进度，
还得在聚合进度里把这些小文件的字节数混进视频流里 —— 得不偿失。

编排本身在 `util/parse/additional/runner.py`，与桌面版**同一份代码**，
两端产出的附加文件因此一致。这里只做两件事：丢到线程池里跑，以及 ASS 弹幕的 Qt 前置。

## ASS 弹幕的例外

ASS 要用 `QFontMetrics` 量弹幕宽度来排轨道，需要进程里有 QGuiApplication。
它**只能在主线程构造**，而附加内容是在工作线程里跑的 —— 所以必须在丢进线程池**之前**、
也就是还在事件循环线程上的时候先建好。建好之后工作线程用 QFontMetrics 是安全的。

Qt 不可用时**直接报错而不是悄悄降级成 XML**：用户选的是 ASS，给出别的格式而不吭声，
要到播放器里看不到弹幕效果时才会发现，那时已经不知道是哪一步出的问题。
"""

from typing import Optional
import asyncio
import logging

from util.common.enum import DanmakuType, DownloadType
from util.download.task.info import TaskInfo
from util.download.task.options import resolve
from util.parse.additional.runner import AdditionalRunner
from util.thread import background

from ..qt_runtime import ensure_gui_application

logger = logging.getLogger(__name__)

def needs_font_metrics(task_info: TaskInfo) -> bool:
    """这个任务的附加内容里有没有需要字体度量的部分（目前只有 ASS 弹幕）"""
    if task_info.Download.type & DownloadType.DANMAKU == 0:
        return False

    return resolve(task_info, "danmaku_type") == DanmakuType.ASS

def run_sync(task_info: TaskInfo) -> None:
    """阻塞跑一遍。给已经在工作线程里的调用方用"""
    AdditionalRunner(task_info).run()

async def run(task_info: TaskInfo) -> None:
    """
    跑一遍附加内容解析

    出错时原样抛出，由调用方决定是记为任务失败还是仅提示 —— 与桌面侧
    `AdditionalParseWorker.error` 的语义一致
    """
    if needs_font_metrics(task_info) and not ensure_gui_application():
        # 这一步必须在主线程完成，所以放在丢进线程池之前
        raise RuntimeError(
            "生成 ASS 弹幕需要 Qt 的字体度量，但当前进程无法建立 QGuiApplication。"
            "请在镜像中安装 PySide6-Essentials 与 CJK 字体，或把弹幕格式改为 XML / JSON")

    await asyncio.wrap_future(background.submit(run_sync, task_info))
