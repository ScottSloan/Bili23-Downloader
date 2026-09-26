"""
检查新版本 —— 桌面侧的外壳

发请求、读响应那部分在 `update_check.py` 里（不依赖 Qt，WebUI 后端也用它）。
这里只剩「用 Qt 的方式把它跑起来」：后台线程 + signal_bus 通知界面。
"""

from PySide6.QtCore import QLocale, QObject, Signal, Slot

from ..common.enum import Language, ToastNotificationCategory
from ..common.signal_bus import signal_bus
from ..common.translator import Translator
from ..thread.async_ import AsyncTask
from ..common.config import config

from .update_check import check_for_update

import logging

logger = logging.getLogger(__name__)

def get_ui_language() -> str:
    """
    界面实际显示的语言

    设为跟随系统时，main.py 按 `QLocale()` 装载翻译文件，这里同样取系统语言，
    更新说明才会与界面是同一种语言
    """
    language = config.get(config.language)

    return QLocale.system().name() if language == Language.AUTO else language.value

class UpdateCheckWorker(QObject):
    success = Signal(dict)
    error = Signal(str)
    finished = Signal()

    def __init__(self, include_preview: bool, locale: str):
        super().__init__()

        self.include_preview = include_preview
        self.locale = locale

    @Slot()
    def run(self):
        try:
            info, error_message = check_for_update(self.include_preview, self.locale)

            if error_message:
                self.error.emit(error_message)
            else:
                self.success.emit(info)

        finally:
            self.finished.emit()

class Updater(QObject):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.manual = False

    def check(self, info: dict):
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

        worker = UpdateCheckWorker(config.get(config.include_prerelease), get_ui_language())
        worker.success.connect(self.check)
        worker.error.connect(self.on_error)

        AsyncTask.run(worker)
