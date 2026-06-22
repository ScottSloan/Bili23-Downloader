from PySide6.QtCore import QObject

from ..network.request import NetworkRequestWorker, RequestType
from ..common.enum import ToastNotificationCategory
from ..common.signal_bus import signal_bus
from ..common.translator import Translator
from ..thread.async_ import AsyncTask
from ..common.config import config

import logging

logger = logging.getLogger(__name__)

class Updater(QObject):
    def __init__(self, parent = None):
        super().__init__(parent)

    def check(self, response: dict):
        latest_version = response["latest_version"]

        version = latest_version["version"]

        info = {
            "should_update": response["should_update"],
            "required": response["required"],
            "version": version,
            "content": latest_version["content"],
            "update_url": latest_version["download_url"]
        }

        if info.get("should_update"):

            if config.get(config.skip_version) == version and not self.manual:
                return
            
            signal_bus.update.show_dialog.emit(info)

            logger.info("检测到新版本：%s，当前版本：%s", version, config.get(config.app_version))

        else:
            if self.manual:
                signal_bus.toast.show.emit(ToastNotificationCategory.SUCCESS, "", Translator.TIP_MESSAGES("ALREADY_LATEST_VERSION"))

    def request_update(self, manual: bool):
        def on_error(error_message: str):
            signal_bus.toast.show_long_message.emit(
                ToastNotificationCategory.ERROR,
                Translator.ERROR_MESSAGES("CHECK_UPDATE_FAILED"),
                error_message
            )

        self.manual = manual

        params = {
            "current_version": config.app_version,
            "current_comparable_version": config.app_comparable_version,
            "include_preview": config.get(config.include_prerelease)
        }

        url = "https://verhub.hanloth.cn/api/v1/public/scottsloan-bili23-downloader/versions/check-update"

        worker = NetworkRequestWorker(url, request_type = RequestType.POST, json_data = params)
        worker.success.connect(self.check)
        worker.error.connect(on_error)

        AsyncTask.run(worker)
