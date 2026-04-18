from PySide6.QtCore import QObject, Signal

from util.parse.additional import DanmakuParser, SubtitlesParser, MetadataParser, CoverParser
from util.common import signal_bus, Translator
from util.common.enum import DownloadType

from ...download.task.info import TaskInfo

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
            self.update_status_label(Translator.TIP_MESSAGES("DOWNLOADING_DANMAKU"))

            parser = DanmakuParser(self.task_info)
            parser.parse()

        if attr & DownloadType.SUBTITLE != 0:
            # 下载字幕
            self.update_status_label(Translator.TIP_MESSAGES("DOWNLOADING_SUBTITLES"))

            parser = SubtitlesParser(self.task_info)
            parser.parse()

        if attr & DownloadType.COVER != 0:
            # 下载封面
            self.update_status_label(Translator.TIP_MESSAGES("DOWNLOADING_COVER"))

            parser = CoverParser(self.task_info)
            parser.parse()

        if attr & DownloadType.METADATA != 0:
            # 下载元数据
            self.update_status_label(Translator.TIP_MESSAGES("SCRAPING_METADATA"))

            parser = MetadataParser(self.task_info)
            parser.parse()

        self.update_status_label("")

    def update_status_label(self, label: str):
        self.task_info.Download.status_label = label

        # 发送信号通知界面更新下载项的显示信息
        signal_bus.download.update_downloading_item.emit(self.task_info)
