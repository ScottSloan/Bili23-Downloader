from ..episode.dynamic import DynamicEpisodeParser
from .favlist import FavlistParser
from .base import ParserBase

from typing import Callable
from threading import Event
import time

class DynamicParser(ParserBase):
    def __init__(self, data: dict, _parser: FavlistParser, update_progress_callback: Callable, stop_event: Event):
        super().__init__()

        self.info_data: dict = data["data"]

        self.url = self.info_data["url"]
        self.start_page = self.info_data["start_page"]
        self.end_page = self.info_data["end_page"]

        self.parser = _parser
        self.stop_event = stop_event
        self.update_progress = update_progress_callback

    def parse(self):
        self.episode_parser = DynamicEpisodeParser(self.info_data, self.parser.get_category_name())
        #self.episode_parser.video_episode_data_parser()

        for page in range(self.start_page, self.end_page + 1):
            if self.stop_event.is_set():
                break

            time.sleep(1)

            self._update_ui_progress(page)

    def _update_ui_progress(self, page: int):
        self.update_progress(f"正在解析第 {page} 页，共 {self.end_page} 页")

        #self.episode_parser.update()

    def get_category_name(self):
        return self.parser.get_category_name()
