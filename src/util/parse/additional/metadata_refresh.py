from PySide6.QtCore import QObject, Signal, Slot

from ...common.enum import DownloadStatus, MetadataType
from ...download.task.info import TaskInfo
from ...network.error import NetworkErrorKind, classify_network_error
from ..episode.tree import Attribute
from .metadata import MetadataParser

from copy import deepcopy
from threading import Event
import logging

logger = logging.getLogger(__name__)


def can_refresh_metadata(task: TaskInfo):
    return bool(task.Download.status == DownloadStatus.COMPLETED and task.Episode.attribute & Attribute.VIDEO_BIT and task.Episode.bvid)


class MetadataRefreshWorker(QObject):
    progress = Signal(int)
    result = Signal(int, int, str)
    finished = Signal()

    def __init__(self, tasks: list[TaskInfo], format: MetadataType, batch_size: int, pause: int):
        super().__init__()
        self.tasks = [deepcopy(task) for task in tasks if can_refresh_metadata(task)]
        self.format = format
        self.batch_size = batch_size
        self.pause = pause
        self.cancelled = Event()

    def cancel(self):
        self.cancelled.set()

    @Slot()
    def run(self):
        succeeded = 0
        failed = 0
        last_error = ""

        try:
            for index, task in enumerate(self.tasks):
                if index and index % self.batch_size == 0:
                    self.cancelled.wait(self.pause)
                if self.cancelled.is_set():
                    break

                try:
                    task.Options.metadata_type = self.format.value
                    MetadataParser(task).parse(refresh = True)
                    succeeded += 1
                except Exception as error:
                    logger.exception("更新视频 %s 的元数据失败", task.Episode.bvid)
                    failed += 1
                    last_error = f"{task.Episode.bvid}: {error}"
                    network = classify_network_error(error)
                    if network and network.kind == NetworkErrorKind.RISK_CONTROL:
                        break

                self.progress.emit(index + 1)
        finally:
            self.result.emit(succeeded, failed, last_error)
            self.finished.emit()
