from PySide6.QtCore import QObject, Signal, Slot

from ..common.data.auto_parse import AutoParsePayload
from ..common.translator import Translator
from ..common.data import url_patterns
from ..common.enum import ParserType
from .episode.tree import EpisodeData
# 认类型与惰性实例化 parser 的那部分本就是纯逻辑，搬到 session.py 与 WebUI 共用
from .session import ParserResolver as WorkerBase

from threading import Event
import logging

logger = logging.getLogger(__name__)

class ParseWorker(WorkerBase, QObject):
    success = Signal(str, dict)
    error = Signal(str)
    finished = Signal()

    def __init__(self, url: str, pn: int = 1):
        super().__init__()

        self.url = url
        self.pn = pn
        self.parser_type = ""

    @Slot()
    def run(self):
        # 整段解析都登记为活跃，期间其他解析发起的 clear_cache() 不会擦掉这里写入的数据
        with EpisodeData.parsing():
            try:
                self.parser_type = self.get_parser_type(self.url)

                self.get_redirect_url()

                parser = self.get_parser(self.parser_type)

                parser.parse(self.url, self.pn)

                self.success.emit(parser.get_category_name(), parser.get_extra_data())

            except Exception as e:
                self.on_error()

                self.error.emit(str(e))

            finally:
                # deleteLater 由 AsyncTask 统一挂在 finished 上，此处不再重复调用
                self.finished.emit()

    def get_redirect_url(self):
        # 短链跳转同样在 session.py 里，两端共用
        self.url, self.parser_type = self.resolve_redirect(self.url)

    def on_error(self):
        logger.exception("解析失败")

class ProgressParseWorker(WorkerBase, QObject):
    # 后台解析线程，负责自动解析流程中的进度回传
    success = Signal(str, dict)
    error = Signal(str)
    finished = Signal()

    update_progress = Signal(str)

    def __init__(self, info_data: AutoParsePayload):
        super().__init__()

        self.data: AutoParsePayload = info_data
        self.stop_event = Event()

    @Slot()
    def run(self):
        # 自动解析是在已有解析结果的基础上继续补充，不清空旧数据，只登记为活跃
        with EpisodeData.parsing(clear_cache = False):
            try:
                parser = self._get_parser()
                parser.parse()

                self.success.emit(parser.get_category_name(), {})

                logger.info("自动解析完成")

            except Exception as e:
                logger.exception("解析失败")

                self.error.emit(str(e))

            finally:
                self.finished.emit()

    def _get_parser(self):
        match self.data.parser_type:
            case ParserType.INTERACTIVE_VIDEO:
                return self._get_interactive_video_parser()

            case ParserType.DYNAMIC:
                return self._get_dynamic_parser()
            
            case ParserType.BATCH:
                return self._get_dynamic_parser()

        raise ValueError(f"Unsupported parser type: {self.data.parser_type}")

    def _get_interactive_video_parser(self):
        from .parser.video import InteractiveVideoParser

        return InteractiveVideoParser(self.data.data, self._update_progress_callback, self.stop_event)

    def _get_dynamic_parser(self):
        from .parser.dynamic import DynamicParser

        parser_type = self.get_parser_type(self.data.url)

        base_parser = self.get_parser(parser_type)

        return DynamicParser(self.data, base_parser, self._update_progress_callback, self.stop_event)

    def _update_progress_callback(self, text: str):
        self.update_progress.emit(text)

    def trigger_stop(self):
        self.stop_event.set()