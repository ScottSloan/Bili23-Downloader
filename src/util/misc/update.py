from util.network.request import NetworkRequestWorker, RequestType
from util.common.enum import ToastNotificationCategory
from util.common.signal_bus import signal_bus
from util.common.translator import Translator
from util.common.config import config
from util.thread import AsyncTask

class Updater:
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

        else:
            if self.manual:
                signal_bus.toast.show.emit(ToastNotificationCategory.SUCCESS, "", Translator.TIP_MESSAGES("ALREADY_LATEST_VERSION"))

    def request_update(self, manual: bool):
        def on_error(error_message: str):
            signal_bus.toast.show_long_message.emit(Translator.ERROR_MESSAGES("CHECK_UPDATE_FAILED"), error_message)

        self.manual = manual

        params = {
            "current_version": config.app_version,
            "current_comparable_version": config.app_comparable_version,
            "include_preview": False
        }

        url = "https://verhub.hanloth.cn/api/v1/public/scottsloan-bili23-downloader/versions/check-update"

        worker = NetworkRequestWorker(url, request_type = RequestType.POST, json_data = params)
        worker.success.connect(self.check)
        worker.error.connect(on_error)

        AsyncTask.run(worker)
