from ...common.data.auto_parse import AutoParsePayload
from ...common.signal_bus import signal_bus
from ...common.config import config

from ..episode.dynamic import DynamicEpisodeParser
from .favlist import FavlistParser
from .base import ParserBase

from typing import Callable
from threading import Event
import time

class DynamicParser(ParserBase):
    def __init__(self, data: AutoParsePayload, base_parser: FavlistParser, update_progress_callback: Callable, stop_event: Event):
        super().__init__()

        self.info_data = data

        self.url = self.info_data.url
        self.start_page = self.info_data.start_page
        self.end_page = self.info_data.end_page

        self.parser = base_parser
        self.parser_type = self.parser.get_parser_type()
        self.stop_event = stop_event
        self.update_progress = update_progress_callback

    def parse(self):
        self.episode_parser = DynamicEpisodeParser(self.info_data.data, self.parser.get_category_name())
        self.episode_parser.init_episode_parser(self.parser_type)
        self.episode_parser.init_root_node("")

        for page in range(self.start_page, self.end_page + 1):
            if self.stop_event.is_set():
                break

            parsed_data = self.parser.parse(self.url, page)

            self.episode_parser.update_page_node(parsed_data)

            self._update_ui_progress(page)

            if page < self.end_page:
                time.sleep(config.get(config.parse_interval))

    def _update_ui_progress(self, page: int):
        self.update_progress(f"正在解析第 {page} 页，共 {self.end_page} 页")

        signal_bus.parse.update_parse_list_count.emit(self.get_category_name())

    def get_category_name(self):
        return self.parser.get_category_name()
