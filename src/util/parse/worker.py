from PySide6.QtCore import QObject, Signal, Slot

from .parser.video import VideoParser, InteractiveVideoParser
from .parser.watch_later import WatchLaterParser
from .parser.festival import FestivalParser
from .parser.popular import PopularParser
from .parser.favlist import FavlistParser
from .parser.history import HistoryParser
from .parser.bangumi import BangumiParser
from .parser.dynamic import DynamicParser
from .parser.cheese import CheeseParser
from .parser.space import SpaceParser
from .parser.list import ListParser
from .parser.b23 import B23Parser

from ..common.translator import Translator
from ..common.data import url_patterns
from ..common.enum import ParserType
from .episode.tree import EpisodeData

from threading import Event
import logging
import re

logger = logging.getLogger(__name__)

class WorkerBase:
    def init_parser(self):
        self.parsers = {
            "video": VideoParser(),
            "bangumi": BangumiParser(),
            "cheese": CheeseParser(),
            "space": SpaceParser(),
            "favlist": FavlistParser(),
            "list": ListParser(),
            "popular": PopularParser(),
            "watch_later": WatchLaterParser(),
            "history": HistoryParser()
        }

    def get_parser_type(self, url: str):
        for parser_type, pattern in url_patterns:
            if re.findall(pattern, url):
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

        self.init_parser()

    @Slot()
    def run(self):
        EpisodeData.clear_cache()

        try:
            self.parser_type = self.get_parser_type(self.url)

            self.get_redirect_url()

            parser: VideoParser = self.parsers.get(self.parser_type)

            parser.parse(self.url, self.pn)

            self.success.emit(parser.get_category_name(), parser.get_extra_data())

        except Exception as e:
            self.on_error()

            self.error.emit(str(e))

        finally:
            self.finished.emit()

            self.clear_cache()

    def get_redirect_url(self):
        _parsers = {
            "b23": B23Parser(),
            "festival": FestivalParser()
        }

        for parser_type, parser in _parsers.items():
            if parser_type in self.url:
                self.url = parser.parse(self.url)

                self.parser_type = self.get_parser_type(self.url)

    def clear_cache(self):
        self.parsers.clear()

        self.deleteLater()

    def on_error(self):
        logger.exception("解析失败")

class ProgressParseWorker(WorkerBase, QObject):
    # 后台解析线程，专门用于解析互动视频，具有实时更新 UI 进度的能力
    success = Signal(str, dict)
    error = Signal(str)
    finished = Signal()

    update_progress = Signal(str)

    def __init__(self, info_data: dict):
        super().__init__()

        self.data = info_data
        self.stop_event = Event()

    @Slot()
    def run(self):
        try:
            parser = self._get_parser(self.data["parser_type"])
            parser.parse()

            self.success.emit(parser.get_category_name(), {})

        except Exception as e:
            logger.exception("解析失败")

            self.error.emit(str(e))

        finally:
            self.finished.emit()

    def _get_parser(self, parser_type):
        match parser_type:
            case ParserType.INTERACTIVE_VIDEO:
                return InteractiveVideoParser(self.data, self._update_progress_callback, self.stop_event)
            
            case ParserType.DYNAMIC:
                self.init_parser()
                
                self.parser_type = self.get_parser_type(self.data["data"]["url"])

                _parser: FavlistParser = self.parsers.get(self.parser_type)
                _parser.auto_mode = True

                return DynamicParser(self.data, _parser, self._update_progress_callback, self.stop_event)

    def _update_progress_callback(self, text: str):
        self.update_progress.emit(text)

    def trigger_stop(self):
        self.stop_event.set()