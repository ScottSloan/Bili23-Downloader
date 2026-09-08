"""
桌面版跑「解析下载链接」的 Qt 外壳

请求、重试、组装那一半已经抽到 `download/parse/download_info.py`（不依赖 Qt），
WebUI 的下载调度器调的是同一份 —— 这里只剩「丢进线程池、跑完把结果投回 GUI 线程」。

**不要把逻辑挪回来。** 挪回来就意味着两端各有一份，而症状会是「同一个视频桌面版下得到、
WebUI 说拿不到链接」这种两边单看都对的问题。
"""

from PySide6.QtCore import QRunnable, QMetaObject, Qt, Q_ARG

from ...common._json import json_dumps

from ..parse.download_info import resolve_download_info
from ..task.info import TaskInfo

import logging

logger = logging.getLogger(__name__)

class ParseWorker(QRunnable):
    def __init__(self, task_info: TaskInfo, parent = None, on_finished = None, stop_event = None):
        super().__init__()

        self.task_info = task_info

        self.parent = parent

        # 用户暂停 / 取消 / 删除任务时置位，重试等待期间要能及时退出
        self.stop_event = stop_event

        # 解析期间本 worker 一直持有 parent 的裸引用，结束时通知 parent 可以安全销毁
        self.on_finished = on_finished

    def run(self):
        try:
            self._run()

        except Exception:
            # 兜底：异常抛到 QRunnable 之外会被 Qt 静默吞掉，出问题时日志里毫无线索
            logger.exception("解析流程异常退出")

        finally:
            if self.on_finished:
                try:
                    self.on_finished()

                except Exception:
                    logger.exception("通知下载器解析结束失败")

    def _run(self):
        try:
            download_info = resolve_download_info(self.task_info, self.stop_event)

        except Exception as e:
            if self.is_stopped():
                # 任务已被叫停，这时候再弹一条失败提示只会让用户困惑
                return

            self.on_parse_error(str(e))

            return

        if download_info is None or self.is_stopped():
            # 解析期间任务被暂停或取消
            return

        QMetaObject.invokeMethod(
            self.parent,
            "on_parse_finished",
            Qt.ConnectionType.QueuedConnection,
            # 不支持直接传字典，传 json 字符串，在主线程再转换回来
            Q_ARG(str, json_dumps(download_info))
        )

    def is_stopped(self) -> bool:
        return self.stop_event is not None and self.stop_event.is_set()

    def on_parse_error(self, error_message: str):
        QMetaObject.invokeMethod(
            self.parent,
            "on_parse_error",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, error_message)
        )
