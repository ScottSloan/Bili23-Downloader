from ...common.data.auto_parse import AutoParsePayload
from ...common.enum import ToastNotificationCategory
from ...common.signal_bus import signal_bus
from ...common.translator import Translator
from ...common.config import config

from ..episode.dynamic import DynamicEpisodeParser
from .favlist import FavlistParser
from .base import ParserBase

from typing import Callable
from threading import Event
import logging
import time

logger = logging.getLogger(__name__)

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

        self.parsed_count = 0

    def parse(self):
        self.episode_parser = DynamicEpisodeParser(self.info_data.data, self.parser.get_category_name())
        self.episode_parser.init_episode_parser(self.parser_type)

        try:
            if self.info_data.url_list:
                self.parse_url_list(self.info_data.url_list)
            else:
                self.parse_page()

        except Exception as e:
            # 发生异常时，停止解析进程
            self.stop_event.set()

            logger.exception("已停止解析，发生错误：%s", str(e))

            page = 0

            # 弹出警告消息框
            signal_bus.toast.show_long_message.emit(
                ToastNotificationCategory.WARNING,
                Translator.ERROR_MESSAGES("PARSING_STOPPED"),
                Translator.ERROR_MESSAGES("PARSING_STOPPED_MESSAGE").format(page = page, error = str(e))
            )

    def parse_page(self):
        for page in range(self.start_page, self.end_page + 1):
            if self.stop_event.is_set():
                break

            self.parsed_count += 1

            parsed_data = self.parser.parse(self.url, page, get_info_data = True)

            episode_count = self.episode_parser.update_page_node(parsed_data)

            self._update_ui_progress(page, episode_count)

            if page < self.end_page:
                time.sleep(config.get(config.auto_parse_interval))

    def parse_url_list(self, url_list: list):
        for url in url_list:
            if self.stop_event.is_set():
                break

            self.parsed_count += 1

            parsed_data = self.parser.parse(url, get_info_data = True)

            episode_count = self.episode_parser.update_page_node(parsed_data)

            self._update_ui_progress(self.parsed_count, episode_count)

            # 每秒解析一条链接
            time.sleep(1)

    def _update_ui_progress(self, page: int, episode_count: int):
        total_page = self.end_page - self.start_page + 1

        self.update_progress(
            Translator.TIP_MESSAGES("PARSING_PAGE").format(
                page = page,
                total_page = total_page,
                progress = int(self.parsed_count / total_page * 100)
            )
        )

        signal_bus.parse.update_parse_list_count.emit(self.get_category_name(), episode_count)

    def get_category_name(self):
        return self.parser.get_category_name()
