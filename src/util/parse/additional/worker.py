from PySide6.QtCore import QObject, Signal, Slot

from ...common.signal_bus import signal_bus
from ...common.translator import Translator
from ...common.enum import DownloadType, ToastNotificationCategory

from ...download.task.info import TaskInfo

from .subtitles import SubtitlesParser
from .metadata import MetadataParser
from .danmaku import DanmakuParser
from .chapter import ChapterParser
from .player import PlayerInfoParser
from .cover import CoverParser

from threading import Lock
import logging
import time

logger = logging.getLogger(__name__)

# 被风控时往往是同一批任务接连失败，每个都弹一次会刷屏；只按时间节流而不是整个进程只提示一次，
# 隔一段时间再出问题时用户仍然能看到
_PLAYER_INFO_WARNING_INTERVAL = 60

_last_player_info_warning = None
_player_info_warning_lock = Lock()

def warn_player_info_skipped():
    global _last_player_info_warning

    # 多个下载任务的附加内容解析可能同时跑在不同线程上
    with _player_info_warning_lock:
        now = time.monotonic()

        if _last_player_info_warning is not None and now - _last_player_info_warning < _PLAYER_INFO_WARNING_INTERVAL:
            return

        _last_player_info_warning = now

    signal_bus.toast.show.emit(
        ToastNotificationCategory.WARNING,
        "",
        Translator.TIP_MESSAGES("PLAYER_INFO_SKIPPED_MESSAGE")
    )

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
        if need_subtitle or need_chapter:
            player_data = self.get_player_data()

            if player_data is None:
                need_subtitle = need_chapter = False

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

    def get_player_data(self):
        """
        请求播放器信息接口，失败时返回 None，由调用方跳过字幕与章节

        这一步发生在音视频已经下载完之后。接口一旦被风控拦下（HTTP 412），异常原先会一路冒到
        run()，整个任务被判为下载失败，几个 GB 的视频就卡在 100% 交付不出去（#488）。字幕与
        章节只是附加内容，不该拖垮主体，因此在这里降级：记日志、给出提示，任务照常走完。

        不做重试：风控按 IP 判定，短时间内重发只会继续被拦（见 network/error.py）
        """
        # httpx 不能在模块顶部导入，否则会被拖进启动路径（smoke_startup 有断言）
        import httpx

        try:
            return PlayerInfoParser(self.task_info).get_data()

        # ValueError 覆盖响应体不是合法 JSON 的情况（两种 JSON 实现的解码错误都是它的子类）
        except (httpx.HTTPError, ValueError):
            logger.warning("获取播放器信息失败，已跳过字幕与章节", exc_info = True)

            warn_player_info_skipped()

            return None

    def update_status_label(self, label: str):
        self.task_info.Download.status_label = label

        # 发送信号通知界面更新下载项的显示信息
        signal_bus.download.update_downloading_item.emit(self.task_info)
