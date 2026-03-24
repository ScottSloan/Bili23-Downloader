from PySide6.QtCore import QObject, Signal

from util.download.task.info import TaskInfo
from util.common.enum import DownloadType

from util.parse.additional.subtitles import SubtitlesParser
from util.parse.additional.metadata import MetadataParser
from util.parse.additional.danmaku import DanmakuParser
from util.parse.additional.cover import CoverParser

import logging

logger = logging.getLogger(__name__)

class AdditionalParseWorker(QObject):
    success = Signal()
    error = Signal(str)
    finished = Signal()

    def __init__(self, task_info: TaskInfo):
        super().__init__()

        self.task_info = task_info

    def run(self):
        try:
            self.__parse()
            self.success.emit()
        
        except Exception as e:
            self.error.emit(str(e))

            logging.exception("附加文件解析失败")

        finally:
            self.finished.emit()

    def __parse(self):
        # 读取 Download Type 标志位，决定下载哪种类型的附加文件
        attr = self.task_info.Download.type

        if attr & DownloadType.DANMAKU != 0:
            # 下载弹幕
            parser = DanmakuParser(self.task_info)
            parser.parse()

        if attr & DownloadType.SUBTITLE != 0:
            # 下载字幕
            parser = SubtitlesParser(self.task_info)
            parser.parse()

        if attr & DownloadType.COVER != 0:
            # 下载封面
            parser = CoverParser(self.task_info)
            parser.parse()

        if attr & DownloadType.METADATA != 0:
            # 下载元数据
            parser = MetadataParser(self.task_info)
            parser.parse()
