from PySide6.QtCore import QObject, Signal, Slot

from util.parse.parser import VideoParser, BangumiParser, CheeseParser, SpaceParser, FavlistParser, ListParser, PopularParser, B23Parser
from util.parse.episode.tree import EpisodeData
from util.common.data import url_patterns

import logging
import re

logger = logging.getLogger(__name__)

class ParseWorker(QObject):
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

            parser: VideoParser = None

            if self.parser_type == "b23":
                # 如果为 b23 短链，则需要先跳转到真实链接
                parser = self.parse_b23_url()

            parser = self.parsers.get(self.parser_type)

            parser.parse(self.url, self.pn)

            self.success.emit(parser.get_category_name(), parser.get_extra_data())

        except Exception as e:
            self.on_error()

            self.error.emit(str(e))

        finally:
            self.finished.emit()

            self.clear_cache()

    def init_parser(self):
        self.parsers = {
            "video": VideoParser(),
            "bangumi": BangumiParser(),
            "cheese": CheeseParser(),
            "space": SpaceParser(),
            "favlist": FavlistParser(),
            "list": ListParser(),
            "popular": PopularParser(),
        }

    def get_parser_type(self, url: str):
        for parser_type, pattern in url_patterns:
            if re.findall(pattern, url):
                return parser_type
            
        raise ValueError(self.tr("Invalid link format"))

    def parse_b23_url(self):
        parser = B23Parser(self.url)

        self.url = parser.redirect()

        self.parser_type = self.get_parser_type(self.url)

        return parser
    
    def clear_cache(self):
        self.parsers.clear()

        self.deleteLater()

    def on_error(self):
        logger.exception("解析失败")
