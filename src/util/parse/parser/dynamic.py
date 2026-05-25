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

        self.parsed_page_count = 0

    def parse(self):
        self.episode_parser = DynamicEpisodeParser(self.info_data.data, self.parser.get_category_name())
        self.episode_parser.init_episode_parser(self.parser_type)

        try:
            for page in range(self.start_page, self.end_page + 1):
                if self.stop_event.is_set():
                    break

                self.parsed_page_count += 1

                parsed_data = self.parser.parse(self.url, page, get_info_data = True)

                self.episode_parser.update_page_node(parsed_data)

                self._update_ui_progress(page)

                if page < self.end_page:
                    time.sleep(config.get(config.auto_parse_interval))

        except Exception as e:
            # 发生异常时，停止解析进程
            self.stop_event.set()

            logger.exception("已停止解析，发生错误：%s", str(e))

            # 弹出警告消息框
            signal_bus.toast.show_long_message.emit(
                ToastNotificationCategory.WARNING,
                Translator.ERROR_MESSAGES("PARSING_STOPPED"),
                Translator.ERROR_MESSAGES("PARSING_STOPPED_MESSAGE").format(page = page, error = str(e))
            )

    def _update_ui_progress(self, page: int):
        total_page = self.end_page - self.start_page + 1

        self.update_progress(
            Translator.TIP_MESSAGES("PARSING_PAGE").format(
                page = page,
                total_page = total_page,
                progress = int(self.parsed_page_count / total_page * 100)
            )
        )

        signal_bus.parse.update_parse_list_count.emit(self.get_category_name())

    def get_category_name(self):
        return self.parser.get_category_name()
