from PySide6.QtCore import QObject, Signal, Slot

from ..common.data.auto_parse import AutoParsePayload
from ..common.translator import Translator
from ..common.data import url_patterns
from ..common.enum import ParserType
from .episode.tree import EpisodeData

from threading import Event
import logging

logger = logging.getLogger(__name__)

# 需要 wbi 签名的解析类型。签名密钥没就绪时，这些类型的解析必然失败。
#
# 刻意把「不需要签名」也列成一份，而不是简单地用「不在前一份里」判断：
# 新增解析器时必须在这里明确表态一次，漏了就会被默认归到不需要签名那一侧，
# 也就是弱网下照样弹出「解析失败」。test_parse_worker.py 会对着源码逐项核对
WBI_PARSER_TYPES = frozenset({"video", "list", "space", "popular", "watch_later"})
NO_WBI_PARSER_TYPES = frozenset({"bangumi", "cheese", "lesson", "favlist", "history", "audio"})

def needs_wbi_signature(parser_type: str) -> bool:
    """
    该解析类型是否需要 wbi 签名。

    b23 / festival 这两种短链不在此列：真实的解析类型要请求一次才知道，
    拦下来可能误伤指向番剧的短链，交给 enc_wbi 的按需补取兜底即可。
    """
    return parser_type in WBI_PARSER_TYPES

class WorkerBase:
    def get_parser(self, parser_type: str):
        match parser_type:
            case "video":
                from .parser.video import VideoParser
                return VideoParser()
            
            case "bangumi":
                from .parser.bangumi import BangumiParser
                return BangumiParser()
            
            case "cheese":
                from .parser.cheese import CheeseParser
                return CheeseParser()

            case "lesson":
                from .parser.lesson import LessonParser
                return LessonParser()

            case "space":
                from .parser.space import SpaceParser
                return SpaceParser()
            
            case "favlist":
                from .parser.favlist import FavlistParser
                return FavlistParser()
            
            case "list":
                from .parser.list import ListParser
                return ListParser()
            
            case "popular":
                from .parser.popular import PopularParser
                return PopularParser()
            
            case "watch_later":
                from .parser.watch_later import WatchLaterParser
                return WatchLaterParser()
            
            case "history":
                from .parser.history import HistoryParser
                return HistoryParser()
            
            case "audio":
                from .parser.audio import AudioParser
                return AudioParser()
            
            case _:
                raise ValueError("未知的解析类型")

    def get_parser_type(self, url: str):
        for parser_type, pattern in url_patterns:
            if pattern.search(url):
                return parser_type
            
        raise ValueError(Translator.ERROR_MESSAGES("INVALID_LINK"))

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
        from .parser.festival import FestivalParser
        from .parser.b23 import B23Parser

        _parsers = {
            "b23": B23Parser(),
            "festival": FestivalParser()
        }

        for parser_type, parser in _parsers.items():
            if parser_type in self.url:
                self.url = parser.parse(self.url)

                self.parser_type = self.get_parser_type(self.url)

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