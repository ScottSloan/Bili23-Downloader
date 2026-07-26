# --------- System Version Check ---------

# 低于 Windows 10 1809 的系统不支持 QT 6

import platform
import ctypes
import locale
import sys


# 标记经过特殊处理、可在 Windows 7 上运行的 PySide 版本。该版本需要在
# 创建 QApplication 前禁用 DirectWrite，否则 Qt 文本会显示为方框。
qt_win7_compatible = False

if sys.platform == "win32":
    def _msw_messagebox(title: str, content: str):
        ctypes.windll.user32.MessageBoxW(0, content, title, 0 | 0x10)

        from PySide6 import __version__

    def _get_messages(lang_tag):
        match lang_tag:
            case "zh_CN" | "zh_SG":
                return (
                    "不支持的 Windows 版本",
                    "本程序需要 Windows 10 1809 (Build 17763) 及更高版本才能运行。\n请升级系统或使用 Windows 7 兼容版。"
                )

            case "zh_TW" | "zh_HK" | "zh_MO":
                return (
                    "不支援的 Windows 版本",
                    "本程式需要 Windows 10 1809 (Build 17763) 及更高版本才能執行。\n請升級系統或使用 Windows 7 相容版。"
                )

            case _:
                return (
                    "Unsupported Windows Version",
                    "This application requires Windows 10 1809 (Build 17763) or later to run.\nPlease upgrade your system or use the Windows 7 compatible version."
                )

    version = platform.version().split(".")
    major, minor, build = map(int, version)

    try:
        from PySide6 import __version_info__

        qt_version = __version_info__

    except ImportError:
        qt_version = (0, 0, 0, "", "")

    qt_win7_compatible = len(qt_version) > 3 and qt_version[3] == "compatible"
    
    # 当系统版本低于 Windows 10 1809 且 QT 版本为 6.x 时，显示不支持的提示并退出程序
    # 对于 Win7 兼容版，qt_version 中已经带有 compatible 字符串，跳过检测

    if (major, minor, build) < (10, 0, 17763) and qt_version[0] == 6 and qt_version[3] != "compatible":
        lang_id = ctypes.windll.kernel32.GetUserDefaultUILanguage()
        lang_tag = locale.windows_locale.get(lang_id, "en_US")

        title, content = _get_messages(lang_tag)

        _msw_messagebox(title, content)

        sys.exit(1)

from PySide6.QtCore import QStandardPaths

from logging.handlers import TimedRotatingFileHandler
from datetime import datetime
from pathlib import Path
import logging
import os

# --------- Logging Configuration ---------

appdata_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)

log_path = Path(appdata_path) / "Bili23 Downloader" / "logs" / "app.log"
log_path.parent.mkdir(parents = True, exist_ok = True)

class CompactLogFormatter(logging.Formatter):
    def format(self, record):
        record.callsite = f"{record.filename}:{record.lineno} in {record.funcName}"
        return super().format(record)

    def formatTime(self, record, datefmt = None):
        dt = datetime.fromtimestamp(record.created)

        if datefmt:
            return dt.strftime(datefmt)
        
        return dt.isoformat(sep = " ", timespec = "microseconds")

log_formatter = CompactLogFormatter(
    "[%(asctime)s] - %(name)s - %(levelname)s - at %(callsite)s: %(message)s",
    datefmt = "%Y-%m-%d %H:%M:%S.%f",
)

stream_handler = logging.StreamHandler(sys.stdout)
stream_handler.setFormatter(log_formatter)

file_handler = TimedRotatingFileHandler(log_path, when = "midnight", interval = 1, backupCount = 15, encoding = "utf-8")
file_handler.setFormatter(log_formatter)

logging.basicConfig(
    level = logging.INFO,
    handlers = [stream_handler, file_handler]
)

# --------- Disable PySide6 Warnings ---------
from PySide6.QtCore import QtMsgType, qInstallMessageHandler

def qt_message_handler(mode, context, message):
    # 忽略特定的 Qt 警告
    if "QFont::setPointSize" in message or "OpenType support missing" in message or "CreateFontFaceFromHDC" in message:
        return
    
    # 其他 Qt 日志转发到 Python logging
    logger = logging.getLogger("Qt")

    if mode == QtMsgType.QtWarningMsg:
        logger.warning(message)

    elif mode == QtMsgType.QtCriticalMsg:
        logger.error(message)

    elif mode == QtMsgType.QtFatalMsg:
        logger.critical(message)

    elif mode == QtMsgType.QtInfoMsg:
        logger.info(message)

    else:
        logger.debug(message)

qInstallMessageHandler(qt_message_handler)

# --------- Imports ---------

from PySide6.QtCore import Qt, QLocale, QTranslator, QLockFile, QTimer
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

from qfluentwidgets import FluentTranslator

from util.common.config import config
import res.resources_rc

INSTANCE_LOCK_NAME = "instance.lock"
INSTANCE_LOCK_TIMEOUT_MS = 10_000
INSTANCE_SERVER_NAME = "bili23_downloader_single_instance"
APP_MUTEX_NAME = "B096F0C1-D105-4EF9-86E1-5E87DA884EA4"

logger = logging.getLogger(__name__)

class Application(QApplication):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.window = None
        self.instance_server: QLocalServer = None
        self.pending_instance_activation = False
        self.app_mutex_handle = None

        self.aboutToQuit.connect(self.cleanup_instance_state)

        self.init_single_instance()

        if sys.platform == "win32":
            self.app_mutex_handle = self._msw_create_mutex(APP_MUTEX_NAME)

    def init_single_instance(self):
        lock_path = Path(appdata_path) / "Bili23 Downloader" / "locks" / INSTANCE_LOCK_NAME

        lock_path.parent.mkdir(parents = True, exist_ok = True)

        self.instance_lock = QLockFile(str(lock_path))
        self.instance_lock.setStaleLockTime(INSTANCE_LOCK_TIMEOUT_MS)

        if self.instance_lock.tryLock(0):
            self.init_instance_server()
            return

        self.instance_lock.removeStaleLockFile()

        if not self.instance_lock.tryLock(0):
            if self.wake_existing_instance():
                sys.exit(0)

            logger.warning("无法获取实例锁，程序已在运行中")
            sys.exit(0)

        self.init_instance_server()

    def init_instance_server(self):
        if self.instance_server is not None:
            return

        QLocalServer.removeServer(INSTANCE_SERVER_NAME)

        self.instance_server = QLocalServer(self)
        self.instance_server.newConnection.connect(self.on_new_instance_connection)

        if not self.instance_server.listen(INSTANCE_SERVER_NAME):
            logger.warning("无法启动实例唤醒服务")

    def on_new_instance_connection(self):
        if self.instance_server is None:
            return

        while self.instance_server.hasPendingConnections():
            socket = self.instance_server.nextPendingConnection()

            if socket is None:
                continue

            socket.disconnectFromServer()
            socket.deleteLater()

        self.activate_existing_instance()

    def wake_existing_instance(self) -> bool:
        socket = QLocalSocket()
        socket.connectToServer(INSTANCE_SERVER_NAME)

        if not socket.waitForConnected(500):
            logger.warning("无法唤醒已运行的实例")
            return False

        socket.write(b"activate")
        socket.flush()
        socket.waitForBytesWritten(500)
        socket.disconnectFromServer()

        return True

    def activate_existing_instance(self):
        if self.window is None:
            self.pending_instance_activation = True
            return

        self.pending_instance_activation = False
        self.window._activate_window()

    def process_pending_instance_activation(self):
        if self.pending_instance_activation:
            self.activate_existing_instance()

    def cleanup_instance_state(self):
        if hasattr(self, "instance_lock"):
            self.instance_lock.unlock()

        if sys.platform == "win32" and hasattr(self, "app_mutex_handle") and self.app_mutex_handle:
            ctypes.windll.kernel32.CloseHandle(self.app_mutex_handle)
            self.app_mutex_handle = None

        if self.instance_server is not None:
            self.instance_server.close()
            QLocalServer.removeServer(INSTANCE_SERVER_NAME)

    def setup_app(self):
        self.setAttribute(Qt.ApplicationAttribute.AA_DontCreateNativeWidgetSiblings)
        
        # 设置默认字体
        self.default_font = self.font()
        self.default_font.setPointSize(10)
        self.default_font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)

        self.setFont(self.default_font)

        # 加载翻译文件
        locale: QLocale = config.get(config.language).value

        self.fluent_translator = FluentTranslator(locale)
        self.bili23_translator = QTranslator()
        self.bili23_translator.load(locale, "bili23", ".", ":/bili23/i18n")

        self.installTranslator(self.fluent_translator)
        self.installTranslator(self.bili23_translator)

    def bootstrap_startup_tasks(self):
        # 将登录态与用户信息初始化放到首屏之后，避免阻塞窗口展示
        from util.auth.cookie import cookie_manager
        from util.auth.user import user_manager

        self.warmup_ssl_context()

        cookie_manager.init_cookie_info()
        user_manager.init_user_info()

    def warmup_ssl_context(self):
        # 首次构建 SSL 上下文需要加载完整的 CA 证书列表（约 0.5 秒）。
        # 提前在后台线程完成，避免第一次发起下载时在 GUI 线程上付出这笔开销。
        from util.network.request import get_ssl_context
        from threading import Thread

        def warmup():
            try:
                get_ssl_context()

            except Exception:
                logger.exception("预热 SSL 上下文失败")

        Thread(target = warmup, name = "ssl-warmup", daemon = True).start()

    def _msw_create_mutex(self, name: str):
        import ctypes
        from ctypes import wintypes

        kernel32 = ctypes.WinDLL("kernel32", use_last_error = True)
        kernel32.CreateMutexW.restype = wintypes.HANDLE

        mutex = kernel32.CreateMutexW(None, False, name)
        if not mutex:
            raise ctypes.WinError(ctypes.get_last_error())

        return mutex

def _main():
    scaling_value = config.get(config.display_scaling).value

    if scaling_value != "Auto":
        os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
        os.environ["QT_SCALE_FACTOR"] = scaling_value

    # Qt 需要在 QApplication 构造时读取平台参数。仅对特殊的 Windows 7
    # 兼容版自动添加参数，同时尊重用户显式传入的 -platform 选项。
    app_args = list(sys.argv)
    if qt_win7_compatible and not any(arg == "-platform" or arg.startswith("-platform=") for arg in app_args):
        app_args.extend(["-platform", "windows:nodirectwrite"])

    app = Application(app_args)
    app.setup_app()
    
    from gui.interface.main_window import MainWindow

    app.window = MainWindow()
    app.process_pending_instance_activation()

    QTimer.singleShot(0, app.bootstrap_startup_tasks)

    app.exec()

if __name__ == "__main__":
    _main()
