from PySide6.QtCore import QObject, Signal, Slot

from ...common.signal_bus import signal_bus
from ...common.translator import Translator
from ...common.enum import DownloadType

from ...download.task.info import TaskInfo

from .subtitles import SubtitlesParser
from .metadata import MetadataParser
from .danmaku import DanmakuParser
from .chapter import ChapterParser
from .player import PlayerInfoParser
from .cover import CoverParser

import logging

logger = logging.getLogger(__name__)

class AdditionalParseWorker(QObject):
    success = Signal()
    error = Signal(str)
    finished = Signal()

    def __init__(self, task_info: TaskInfo):
        super().__init__()

        self.task_info = task_info

    @Slot()
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

        # 待嵌入的字幕轨在下方逐条追加。任务暂停恢复或失败重试时会重新走一遍附加内容解析，
        # 不先清空就会把同一个 ASS 文件重复登记，最终被嵌入多条相同的轨道
        self.task_info.File.subtitle_track_list.clear()

        need_subtitle = attr & DownloadType.SUBTITLE != 0
        need_chapter = ChapterParser.is_available(self.task_info)

        if attr & DownloadType.DANMAKU != 0:
            # 下载弹幕
            self.update_status_label(Translator.TIP_MESSAGES("DOWNLOADING_DANMAKU"))

            parser = DanmakuParser(self.task_info)
            parser.parse()

        # 字幕和章节来自同一个播放器信息接口，只请求一次
        player_data = PlayerInfoParser(self.task_info).get_data() if need_subtitle or need_chapter else {}

        if need_subtitle:
            # 下载字幕
            self.update_status_label(Translator.TIP_MESSAGES("DOWNLOADING_SUBTITLES"))

            parser = SubtitlesParser(self.task_info)
            parser.parse(player_data)

        if need_chapter:
            # 获取章节信息，生成供 FFmpeg 使用的章节文件
            self.update_status_label(Translator.TIP_MESSAGES("PARSING_CHAPTER"))

            parser = ChapterParser(self.task_info)
            parser.parse(player_data)

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
