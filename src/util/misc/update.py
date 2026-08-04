from PySide6.QtCore import QObject, Signal, Slot

from verhub_sdk import VerhubClient

from ..common.enum import ToastNotificationCategory
from ..common.signal_bus import signal_bus
from ..common.translator import Translator
from ..thread.async_ import AsyncTask
from ..common.config import config

import requests
import logging

logger = logging.getLogger(__name__)

VERHUB_BASE_URL = "https://verhub.hanloth.cn/api/v1"
VERHUB_PROJECT_KEY = "scottsloan-bili23-downloader"

class CheckUpdateWorker(QObject):
    success = Signal(object)
    error = Signal(str)
    finished = Signal()

    @Slot()
    def run(self):
        from ..network.proxy import Proxy

        try:
            session = None

            if proxies := Proxy().get_proxies():
                session = requests.Session()
                session.proxies.update(proxies)

            with VerhubClient(
                VERHUB_BASE_URL,
                VERHUB_PROJECT_KEY,
                session = session,
                app_identifier = f"Bili23-Downloader/{config.app_version}"
            ) as client:
                response = client.public.check_update(
                    current_version = config.app_version,
                    current_comparable_version = config.app_comparable_version,
                    include_preview = config.get(config.include_prerelease)
                )

            self.success.emit(response)

        except Exception as e:
            self.error.emit(str(e))

        finally:
            self.finished.emit()

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

        worker = CheckUpdateWorker()
        worker.success.connect(self.check)
        worker.error.connect(on_error)

        AsyncTask.run(worker)
