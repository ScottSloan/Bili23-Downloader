"""
检查新版本 —— 桌面侧的外壳

拼请求、读响应那部分在 `update_check.py` 里（不依赖 Qt，WebUI 后端也用它）。
这里只剩「用 Qt 的方式把它跑起来」：异步 worker + signal_bus 通知界面。
"""

from PySide6.QtCore import QObject

from ..common.enum import ToastNotificationCategory
from ..common.signal_bus import signal_bus
from ..common.translator import Translator
from ..network.request import RequestType
from ..network.worker import NetworkRequestWorker
from ..thread.async_ import AsyncTask
from ..common.config import config

from .update_check import (
    CHECK_UPDATE_URL, build_headers, build_payload, get_error_message, parse_response
)

import logging

logger = logging.getLogger(__name__)

class Updater(QObject):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.manual = False

    def check(self, response: dict):
        # 服务端返回非 2xx 时响应体形如 {"statusCode": 400, "message": "..."}，此处统一按错误处理
        if error_message := get_error_message(response):
            self.on_error(error_message)
            return

        info = parse_response(response)

        version = info["version"]

        if info.get("should_update"):

            if config.get(config.skip_version) == version and not self.manual:
                return

            signal_bus.update.show_dialog.emit(info)

            logger.info("检测到新版本：%s，当前版本：%s", version, config.app_version)

        else:
            if self.manual:
                signal_bus.toast.show.emit(ToastNotificationCategory.SUCCESS, "", Translator.TIP_MESSAGES("ALREADY_LATEST_VERSION"))

    def on_error(self, error_message: str):
        logger.error("检查更新失败：%s", error_message)

        signal_bus.toast.show_long_message.emit(
            ToastNotificationCategory.ERROR,
            Translator.ERROR_MESSAGES("CHECK_UPDATE_FAILED"),
            error_message
        )

    def request_update(self, manual: bool):
        self.manual = manual

        worker = NetworkRequestWorker(
            url = CHECK_UPDATE_URL,
            request_type = RequestType.POST,
            json_data = build_payload(config.get(config.include_prerelease)),
            raise_for_status = False,
            content_type = "application/json",
            extra_headers = build_headers()
        )
        worker.success.connect(self.check)
        worker.error.connect(self.on_error)

        AsyncTask.run(worker)
