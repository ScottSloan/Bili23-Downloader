import platform
import ctypes
import locale
import sys

# --------- MCP stdio 桥接 ---------

if "--mcp-stdio" in sys.argv:
    from util.mcp.stdio_bridge import run_stdio_bridge

    sys.exit(run_stdio_bridge())

# --------- WebUI 分流 ---------

if "--web-ui" in sys.argv:
    from web.entry import run_web_ui

    sys.exit(run_web_ui(sys.argv))

# --------- System Version Check ---------

# 低于 Windows 10 1809 的系统不支持 QT 6

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

from datetime import datetime
from pathlib import Path
import logging
import os

# --------- Logging Configuration ---------

from util.common._config.paths import get_data_dir
from util.common.logging_setup import setup_logging

appdata_path = get_data_dir()

log_path = setup_logging("app.log")

# --------- Crash Handler ---------

import faulthandler
import threading
import atexit

crash_log_path = log_path.parent / "crash.log"

# 崩溃栈是追加写入的，文件过大时先归档，避免历史记录无限堆积
if crash_log_path.exists() and crash_log_path.stat().st_size > 1024 * 1024:
    crash_log_path.replace(crash_log_path.with_suffix(".log.old"))

# faulthandler 只保留 fileno，必须持有文件对象本身，否则被 GC 关闭后写入的是失效的描述符
crash_log_file = open(crash_log_path, "a", encoding = "utf-8")

def write_crash_log(reason: str, dump_traceback: bool = False):
    timestamp = datetime.now().isoformat(sep = " ", timespec = "milliseconds")

    crash_log_file.write(f"\n{'=' * 78}\n[{timestamp}] {reason}\n{'=' * 78}\n")
    crash_log_file.flush()

    if dump_traceback:
        faulthandler.dump_traceback(file = crash_log_file, all_threads = True)

        crash_log_file.flush()

# 每次启动都写一条分隔标记，用于区分本次运行与历史崩溃记录
write_crash_log(f"进程启动，PID {os.getpid()}")

faulthandler.enable(file = crash_log_file, all_threads = True)

def handle_uncaught_exception(exc_type, exc_value, exc_traceback):
    # 主线程中未被捕获的 Python 异常
    if issubclass(exc_type, KeyboardInterrupt):
        sys.__excepthook__(exc_type, exc_value, exc_traceback)

        return

    logging.getLogger("crash").critical("主线程未捕获的异常", exc_info = (exc_type, exc_value, exc_traceback))

    write_crash_log(f"主线程未捕获的异常：{exc_type.__name__}: {exc_value}", dump_traceback = True)

def handle_uncaught_thread_exception(args):
    # 子线程中未被捕获的 Python 异常，默认只打到 stderr，打包后会直接丢失
    if issubclass(args.exc_type, SystemExit):
        return

    thread_name = args.thread.name if args.thread else "unknown"

    logging.getLogger("crash").critical(
        "子线程 %s 未捕获的异常", thread_name, exc_info = (args.exc_type, args.exc_value, args.exc_traceback)
    )

    write_crash_log(f"子线程 {thread_name} 未捕获的异常：{args.exc_type.__name__}: {args.exc_value}", dump_traceback = True)

sys.excepthook = handle_uncaught_exception
threading.excepthook = handle_uncaught_thread_exception

_shutting_down = False

def _on_normal_exit():
    global _shutting_down

    _shutting_down = True

    write_crash_log("进程正常退出")

atexit.register(_on_normal_exit)

def shutdown_process(exit_code: int = 0):
    global _shutting_down

    # 本函数走 os._exit()，atexit 不会执行，因此在这里置位
    _shutting_down = True

    write_crash_log("进程正常退出")

    try:
        logging.shutdown()

    except Exception:
        pass

    for stream in (sys.stdout, sys.stderr):
        try:
            stream.flush()

        except Exception:
            pass

    os._exit(exit_code)

# --------- Disable PySide6 Warnings ---------
from PySide6.QtCore import QtMsgType, qInstallMessageHandler

THREAD_SAFETY_WARNINGS = (
    "Cannot create children for a parent that is in a different thread",
    "Cannot send events to objects owned by a different thread",
    "Timers cannot be stopped from another thread",
    "Destroyed while thread is still running",
    "was not called from the main thread",
    "QThreadStorage",
)

_dumped_thread_warnings = set()

def qt_message_handler(mode, context, message):
    # 忽略特定的 Qt 警告
    if "QFont::setPointSize" in message or "OpenType support missing" in message or "CreateFontFaceFromHDC" in message:
        return

    # 其他 Qt 日志转发到 Python logging
    logger = logging.getLogger("Qt")

    if mode == QtMsgType.QtWarningMsg:
        logger.warning(message)

        if not _shutting_down:
            for marker in THREAD_SAFETY_WARNINGS:
                if marker in message and marker not in _dumped_thread_warnings:
                    _dumped_thread_warnings.add(marker)

                    write_crash_log(f"Qt 线程安全警告：{message}", dump_traceback = True)

                    break

    elif mode == QtMsgType.QtCriticalMsg:
        logger.error(message)

    elif mode == QtMsgType.QtFatalMsg:
        # qFatal 之后 Qt 会立即 abort，这是最后的记录机会
        logger.critical(message)

        for handler in logging.getLogger().handlers:
            handler.flush()

        write_crash_log(f"Qt 致命错误：{message}", dump_traceback = True)

    elif mode == QtMsgType.QtInfoMsg:
        logger.info(message)

    else:
        logger.debug(message)

qInstallMessageHandler(qt_message_handler)

# --------- Imports ---------

from PySide6.QtCore import Qt, QLocale, QTranslator, QTimer, Signal, QCoreApplication
from PySide6.QtNetwork import QLocalServer, QLocalSocket
from PySide6.QtWidgets import QApplication, QMessageBox
from PySide6.QtGui import QFont

from qfluentwidgets import FluentTranslator

from util.common.config import config
from util.common.enum import Language
from util.common.single_instance import InstanceLock, INSTANCE_LOCK_NAME, MODE_GUI
from util.common.translator import set_translate_function
from gui.config_bridge import install as install_config_bridge
import res.resources_rc

install_config_bridge()

set_translate_function(QCoreApplication.translate)

INSTANCE_SERVER_NAME = "bili23_downloader_single_instance"
APP_MUTEX_NAME = "B096F0C1-D105-4EF9-86E1-5E87DA884EA4"

INSTANCE_COMMAND_ACTIVATE = b"activate"
INSTANCE_COMMAND_ENSURE_RUNNING = b"ensure-running"

ENSURE_RUNNING_FLAG = "--ensure-running"

logger = logging.getLogger(__name__)

class Application(QApplication):
    # 网络栈在后台线程预热完成后发出，用于把后续的登录态初始化切回 GUI 线程
    network_ready = Signal()

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.window = None
        self.instance_server: QLocalServer = None
        self.pending_instance_activation = False
        self.app_mutex_handle = None

        # 由 MCP 桥接脚本拉起时只需确认进程存在，不要抢用户的焦点
        self.ensure_running_mode = ENSURE_RUNNING_FLAG in sys.argv

        self.aboutToQuit.connect(self.cleanup_instance_state)
        self.network_ready.connect(self.init_auth_info)

        self.init_single_instance()

        if sys.platform == "win32":
            self.app_mutex_handle = self._msw_create_mutex(APP_MUTEX_NAME)

    def init_single_instance(self):
        self.instance_lock = InstanceLock(appdata_path / "locks" / INSTANCE_LOCK_NAME, MODE_GUI)

        if self.instance_lock.acquire():
            self.init_instance_server()

            return

        command = INSTANCE_COMMAND_ENSURE_RUNNING if self.ensure_running_mode else INSTANCE_COMMAND_ACTIVATE

        if self.wake_existing_instance(command):
            sys.exit(0)

        description = self.instance_lock.describe_holder()

        logger.warning("无法获取实例锁，%s", description)

        if not self.ensure_running_mode:
            self._show_instance_conflict(description)

        sys.exit(0)

    def _show_instance_conflict(self, description: str):
        """
        提示锁被另一边占着

        此时翻译器还没装（`setup_app` 才装），所以按用户配置的语言手工选一份文案 ——
        与上方 Windows 版本检查的做法一致
        """
        from util.common.enum import Language

        language = config.get(config.language)

        if language == Language.AUTO:
            language = Language.ENGLISH if not QLocale.system().name().startswith("zh") else (
                Language.CHINESE_TRADITIONAL
                if QLocale.system().name() in ("zh_TW", "zh_HK", "zh_MO")
                else Language.CHINESE_SIMPLIFIED
            )

        title, hint = {
            Language.CHINESE_SIMPLIFIED: (
                "无法启动",
                "{}。\n\n桌面版与 WebUI 共用配置与任务数据，同一时间只能运行一个。"),
            Language.CHINESE_TRADITIONAL: (
                "無法啟動",
                "{}。\n\n桌面版與 WebUI 共用設定與任務資料，同一時間只能執行一個。"),
        }.get(language, (
            "Cannot Start",
            "{}.\n\nThe desktop app and the WebUI share the same config and task data, "
            "so only one can run at a time."))

        try:
            QMessageBox.warning(None, title, hint.format(description))

        except Exception:
            # 弹窗失败不该拦住退出流程
            logger.exception("显示实例冲突提示失败")

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

        should_activate = False

        while self.instance_server.hasPendingConnections():
            socket = self.instance_server.nextPendingConnection()

            if socket is None:
                continue

            command = INSTANCE_COMMAND_ACTIVATE

            if socket.waitForReadyRead(200):
                command = bytes(socket.readAll().data()).strip() or INSTANCE_COMMAND_ACTIVATE

            socket.disconnectFromServer()
            socket.deleteLater()

            if command != INSTANCE_COMMAND_ENSURE_RUNNING:
                should_activate = True

        if should_activate:
            self.activate_existing_instance()

    def wake_existing_instance(self, command: bytes = INSTANCE_COMMAND_ACTIVATE) -> bool:
        socket = QLocalSocket()
        socket.connectToServer(INSTANCE_SERVER_NAME)

        if not socket.waitForConnected(500):
            logger.warning("无法唤醒已运行的实例")
            return False

        socket.write(command)
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
        self.stop_mcp_server()

        if hasattr(self, "instance_lock"):
            self.instance_lock.release()

        if sys.platform == "win32" and hasattr(self, "app_mutex_handle") and self.app_mutex_handle:
            ctypes.windll.kernel32.CloseHandle(self.app_mutex_handle)
            self.app_mutex_handle = None

        if self.instance_server is not None:
            self.instance_server.close()
            QLocalServer.removeServer(INSTANCE_SERVER_NAME)

    def stop_mcp_server(self):
        try:
            from util.mcp import stop_mcp_server

            stop_mcp_server()

        except Exception:
            logger.exception("停止 MCP 服务器失败")

    def setup_app(self):
        self.setAttribute(Qt.ApplicationAttribute.AA_DontCreateNativeWidgetSiblings)

        self.setApplicationName("Bili23 Downloader")
        self.setApplicationDisplayName("Bili23 Downloader")
        self.setDesktopFileName("bili23-downloader")

        # 设置默认字体
        self.default_font = self.font()
        self.default_font.setPointSize(10)
        self.default_font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)

        self.setFont(self.default_font)

        language = config.get(config.language)

        locale = QLocale() if language == Language.AUTO else QLocale(language.value)

        self.fluent_translator = FluentTranslator(locale)
        self.bili23_translator = QTranslator()
        self.bili23_translator.load(locale, "bili23", ".", ":/bili23/i18n")

        self.installTranslator(self.fluent_translator)
        self.installTranslator(self.bili23_translator)

    def bootstrap_startup_tasks(self):
        # 网络栈预热与登录态初始化都放到首屏之后，避免阻塞窗口展示
        self.warmup_network_stack()

        self.start_mcp_server()

    def start_mcp_server(self):
        if not config.get(config.mcp_enabled):
            return

        try:
            from util.mcp import start_mcp_server

            start_mcp_server()

        except Exception:
            # 端口占用、配置异常都不能影响程序本身可用
            logger.exception("启动 MCP 服务器失败")

    def warmup_network_stack(self):
        from threading import Thread

        def warmup():
            try:
                import httpx  # noqa: F401

                from util.network.request import get_ssl_context

                get_ssl_context()

            except Exception:
                logger.exception("预热网络栈失败")

            # Qt 对象只能在 GUI 线程创建，通过跨线程信号切回主线程再发起请求
            self.network_ready.emit()

        Thread(target = warmup, name = "network-warmup", daemon = True).start()

    def init_auth_info(self):
        from util.auth.cookie import cookie_manager
        from util.auth.user import user_manager

        cookie_manager.init_cookie_info()
        user_manager.init_user_info()

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

    if sys.platform == "linux":
        if "QT_QPA_PLATFORM" not in os.environ:
            os.environ["QT_QPA_PLATFORM"] = "xcb;wayland"

        if "RESOURCE_NAME" not in os.environ:
            os.environ["RESOURCE_NAME"] = "bili23-downloader"

    app_args = [arg for arg in sys.argv if arg != ENSURE_RUNNING_FLAG]

    if qt_win7_compatible and not any(arg == "-platform" or arg.startswith("-platform=") for arg in app_args):
        app_args.extend(["-platform", "windows:nodirectwrite"])

    app = Application(app_args)
    app.setup_app()

    from util.thread.dispatcher import install_qt_dispatcher

    install_qt_dispatcher()

    from gui.interface.main_window import MainWindow

    app.window = MainWindow()
    app.process_pending_instance_activation()

    QTimer.singleShot(0, app.bootstrap_startup_tasks)

    exit_code = app.exec()

    shutdown_process(exit_code)

if __name__ == "__main__":
    _main()
