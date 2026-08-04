from PySide6.QtCore import QObject

from ..common.enum import ToastNotificationCategory
from ..common.signal_bus import signal_bus
from ..common.translator import Translator
from ..network.request import NetworkRequestWorker, RequestType
from ..thread.async_ import AsyncTask
from ..common.config import config

import sys
import logging

logger = logging.getLogger(__name__)

VERHUB_BASE_URL = "https://verhub.hanloth.cn/api/v1"
VERHUB_PROJECT_KEY = "scottsloan-bili23-downloader"

# 客户端来源声明，仅供服务端统计使用，不影响接口返回内容
PLATFORM_HEADER = "x-verhub-platform"
PLATFORM_VERSION_HEADER = "x-verhub-platform-version"

# 系统版本明细的长度上限，与服务端一致，超出直接截断
MAX_PLATFORM_VERSION_LENGTH = 32

# 老 Windows 的 NT 内核号 → 市场版本号，Win10 / Win11 均为 10.0，另按构建号区分
WINDOWS_NT_TO_MARKET = {
    (6, 1): "7",
    (6, 2): "8",
    (6, 3): "8.1"
}

def get_platform():
    # 只区分服务端契约中的取值，认不出时返回 others
    if sys.platform.startswith("win"):
        return "windows"

    if sys.platform == "darwin":
        return "macos"

    if sys.platform.startswith("linux"):
        return "linux"

    return "others"

def get_platform_version():
    # 版本探测纯属锦上添花，取不到就返回空串，交给服务端从 User-Agent 兜底推断
    try:
        if sys.platform.startswith("win"):
            info = sys.getwindowsversion()

            # Win11 仍上报内核 10.0，只有构建号 >= 22000 能区分出来
            if info.major == 10 and info.minor == 0:
                return "11" if info.build >= 22000 else "10"

            return WINDOWS_NT_TO_MARKET.get((info.major, info.minor), "")

        if sys.platform == "darwin":
            import platform

            return platform.mac_ver()[0]

        if sys.platform.startswith("linux"):
            import platform

            data = platform.freedesktop_os_release()

            return f"{(data.get('ID') or '').strip().lower()} {(data.get('VERSION_ID') or '').strip()}"

    except Exception:
        return ""

    return ""

def sanitize_platform_version(value: str):
    # 请求头只能承载 ASCII，非可打印字符一律当作空白处理，折叠连续空白后截断，避免编码请求头时抛出异常
    ascii_only = "".join(char if " " < char <= "~" else " " for char in value)

    return " ".join(ascii_only.split())[:MAX_PLATFORM_VERSION_LENGTH].rstrip()

class Updater(QObject):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.manual = False

    def check(self, response: dict):
        # 服务端返回非 2xx 时响应体形如 {"statusCode": 400, "message": "..."}，此处统一按错误处理
        if error_message := self.get_error_message(response):
            self.on_error(error_message)
            return

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
            url = f"{VERHUB_BASE_URL}/public/{VERHUB_PROJECT_KEY}/versions/check-update",
            request_type = RequestType.POST,
            json_data = {
                "current_version": config.app_version,
                "current_comparable_version": config.app_comparable_version,
                "include_preview": config.get(config.include_prerelease)
            },
            raise_for_status = False,
            content_type = "application/json",
            extra_headers = self.get_extra_headers()
        )
        worker.success.connect(self.check)
        worker.error.connect(self.on_error)

        AsyncTask.run(worker)

    @staticmethod
    def get_extra_headers():
        headers = {
            "User-Agent": f"Bili23-Downloader/{config.app_version}",
            PLATFORM_HEADER: get_platform()
        }

        # 取不到系统版本明细时不发这个头
        if platform_version := sanitize_platform_version(get_platform_version()):
            headers[PLATFORM_VERSION_HEADER] = platform_version

        return headers

    @staticmethod
    def get_error_message(response: dict):
        if isinstance(response, dict) and "should_update" in response:
            return None

        message = response.get("message") if isinstance(response, dict) else None

        # 校验失败时 message 为字符串数组
        if isinstance(message, list):
            return "；".join(str(item) for item in message)

        return str(message) if message else Translator.ERROR_MESSAGES("UNKNOWN_ERROR")
