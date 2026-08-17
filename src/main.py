import platform
import ctypes
import locale
import sys

# --------- MCP stdio 桥接 ---------

# 只认 stdio 传输的 MCP 客户端（如 Claude Desktop）会把本程序当作服务器拉起，
# 此时只做 stdio ↔ HTTP 转发，不启动界面。
#
# 这段必须排在所有其他逻辑之前：桥接进程不需要 GUI，也就不该为它加载 Qt，
# 更不该走下面的 Windows 版本检查（能连上的程序本身就跑在受支持的系统上）。

if "--mcp-stdio" in sys.argv:
    from util.mcp.stdio_bridge import run_stdio_bridge

    sys.exit(run_stdio_bridge())

# --------- System Version Check ---------

# 低于 Windows 10 1809 的系统不支持 QT 6


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

# --------- Crash Handler ---------

# Qt 内部的访问违例、qFatal 等原生崩溃不经过 Python 异常机制，进程会被直接终止，
# app.log 里不会留下任何痕迹，表现为"无预兆退出"。faulthandler 在收到 SIGSEGV /
# EXCEPTION_ACCESS_VIOLATION 等信号时，直接通过文件描述符写出所有线程的 Python 栈，
# 不依赖仍然可用的解释器状态，是这类崩溃唯一能拿到的现场。
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

# 进程退出阶段 Qt 与解释器都在拆各自的状态，此时冒出来的线程警告没有诊断价值 ——
# 进程马上就结束了，不会再演变成访问违例。置位后不再记录这类警告，
# 以免每次正常退出都往崩溃日志里灌一份无用的栈，并盖过"进程正常退出"这行标记
_shutting_down = False

def _on_normal_exit():
    global _shutting_down

    _shutting_down = True

    write_crash_log("进程正常退出")

# 正常退出会留下这条记录。崩溃日志末尾若没有它，说明进程是被强行终止的，
# 据此可以区分"硬崩溃"与"意外走到了正常退出流程"
atexit.register(_on_normal_exit)

def shutdown_process(exit_code: int = 0):
    """
    结束进程，跳过解释器的清理流程

    QThread 若在仍然运行时被析构，Qt 会直接 qFatal 中止进程，在 Windows 上表现为
    0xC0000409（FAST_FAIL_FATAL_APP_EXIT），日志里只留下一行
    "QThread: Destroyed while thread is still running"，没有任何 Python 栈。

    退出时总有一些线程停不下来：卡在尚未超时的网络请求里的 worker、仍在转码的 FFmpeg、
    阻塞在注册表通知上的系统主题监听。它们的 QThread 由 Python 侧持有所有权，
    解释器清理模块全局变量时会连带析构，于是"正常退出"变成了崩溃。
    shiboken 的 invalidate() 拦不住这一步（实测 isValid 仍为 True），
    唯一可靠的办法是不给解释器清理的机会 —— 落盘工作在调用本函数之前均已完成，
    剩下的线程交给操作系统随进程一起回收。
    """
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

# 这类警告意味着 Qt 的内部状态已经被破坏，紧随其后往往就是访问违例。
#
# 崩溃真正发生时，主线程通常已经停在 app.exec() 里，faulthandler 打出来的栈上
# 没有任何业务代码的线索（只能看到 _main 一帧）。而警告发出的这一刻，做出跨线程
# 操作的那个线程还在栈上，此时记录全部线程的 Python 栈，比事后从崩溃现场倒推
# 有效得多 —— 它能直接指出是谁在什么位置动了不属于自己线程的对象。
THREAD_SAFETY_WARNINGS = (
    "Cannot create children for a parent that is in a different thread",
    "Cannot send events to objects owned by a different thread",
    "Timers cannot be stopped from another thread",
    "Destroyed while thread is still running",
    "was not called from the main thread",
    "QThreadStorage",
)

# 同一类警告可能在短时间内反复出现，每次都 dump 会把 crash.log 撑爆，
# 而重复的栈并不会带来新信息，因此每个标记只记录首次。
# 多线程并发命中时最多多写一份，不影响判断，无需加锁
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

from PySide6.QtCore import Qt, QLocale, QTranslator, QLockFile, QTimer, Signal
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

# 唤醒已有实例时携带的命令字。activate 会把窗口拉到前台，ensure-running 只是
# 确认进程存在（MCP 桥接脚本用它拉起程序，此时弹出窗口只会打断用户手头的事）
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
        lock_path = Path(appdata_path) / "Bili23 Downloader" / "locks" / INSTANCE_LOCK_NAME

        lock_path.parent.mkdir(parents = True, exist_ok = True)

        self.instance_lock = QLockFile(str(lock_path))
        self.instance_lock.setStaleLockTime(INSTANCE_LOCK_TIMEOUT_MS)

        if self.instance_lock.tryLock(0):
            self.init_instance_server()
            return

        self.instance_lock.removeStaleLockFile()

        if not self.instance_lock.tryLock(0):
            command = INSTANCE_COMMAND_ENSURE_RUNNING if self.ensure_running_mode else INSTANCE_COMMAND_ACTIVATE

            if self.wake_existing_instance(command):
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

        should_activate = False

        while self.instance_server.hasPendingConnections():
            socket = self.instance_server.nextPendingConnection()

            if socket is None:
                continue

            # 读出命令字再决定是否抢焦点。第二个实例总是先写命令再断开，
            # 因此这里只需等一小段时间；读不到内容时按旧行为激活窗口，
            # 保证与不发送命令字的旧版本兼容
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
        # MCP 的监听线程必须在这里收敛。它由 Python 侧持有，若留到解释器清理
        # 全局变量时才被析构，"正常退出"就会变成崩溃 —— 与 shutdown_process()
        # 注释里描述的是同一类问题
        self.stop_mcp_server()

        if hasattr(self, "instance_lock"):
            self.instance_lock.unlock()

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

        # Qt 默认从 argv[0] 推导应用名与 X11 的 WM_CLASS。打包后入口是 _pystand_static.int，
        # 桌面环境据此无法把窗口与 bili23-downloader.desktop 关联，任务栏里的图标和名称都不对。
        # desktop_file_name 同时决定 Wayland 下的 app_id。
        #
        # 注意：AppDataLocation 会拼接 application_name，这里必须晚于模块导入期
        # （main.py 与 util/common/config.py 中的 appdata_path 均在导入期取值），
        # 否则用户数据目录会平移一层。
        self.setApplicationName("Bili23 Downloader")
        self.setApplicationDisplayName("Bili23 Downloader")
        self.setDesktopFileName("bili23-downloader")

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
        # 网络栈预热与登录态初始化都放到首屏之后，避免阻塞窗口展示
        self.warmup_network_stack()

        self.start_mcp_server()

    def start_mcp_server(self):
        # 默认关闭，未启用时连模块都不导入 —— http.server 与整条解析、下载链路
        # 都不应该出现在启动路径上（test/smoke_startup.py 对此有断言）。
        #
        # 这里已经晚于 init_single_instance()，非主实例早在 __init__ 里就退出了，
        # 因此不必再判断自己是不是主实例
        if not config.get(config.mcp_enabled):
            return

        try:
            from util.mcp import start_mcp_server

            start_mcp_server()

        except Exception:
            # 端口占用、配置异常都不能影响程序本身可用
            logger.exception("启动 MCP 服务器失败")

    def warmup_network_stack(self):
        # 导入 httpx 需要连带加载 httpcore 等一系列模块（约 0.3 秒），首次构建 SSL 上下文
        # 需要加载完整的 CA 证书列表（约 0.5 秒）。两者都放到后台线程完成，避免在 GUI 线程
        # 上付出这笔开销。
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
        # Qt 只要检测到 WAYLAND_DISPLAY 就优先选用 wayland 平台插件。而 Wayland 下窗口装饰
        # 归客户端负责，qframelesswindow 的 LinuxWindowEffect.addShadowEffect() 在 Linux 上
        # 又是空实现，无边框窗口不会有任何阴影；走 xcb（Wayland 会话下经由 Xwayland）则由
        # mutter / kwin 绘制服务端阴影。
        #
        # 这里用分号分隔的候选列表而不是写死 xcb：xcb 插件自 Qt 6.5 起依赖 libxcb-cursor0，
        # 便携版没有包管理器的依赖声明兜底，缺库时 xcb 会初始化失败。列成 "xcb;wayland" 后
        # Qt 会自动退到 wayland，代价只是没有阴影，而不是整个程序起不来。
        if "QT_QPA_PLATFORM" not in os.environ:
            os.environ["QT_QPA_PLATFORM"] = "xcb;wayland"

        # WM_CLASS 的实例名部分，Qt 优先取 RESOURCE_NAME，其次是 argv[0] 的文件名。打包后
        # argv[0] 是 _pystand_static.int，桌面环境据此无法把窗口关联到 bili23-downloader.desktop，
        # 任务栏中的图标和名称都会回退成默认值。
        if "RESOURCE_NAME" not in os.environ:
            os.environ["RESOURCE_NAME"] = "bili23-downloader"

    # Qt 需要在 QApplication 构造时读取平台参数。仅对特殊的 Windows 7
    # 兼容版自动添加参数，同时尊重用户显式传入的 -platform 选项。
    #
    # --ensure-running 是本程序自己的开关（见 Application.ensure_running_mode），
    # 不传给 Qt，避免它对未知参数发出警告
    app_args = [arg for arg in sys.argv if arg != ENSURE_RUNNING_FLAG]

    if qt_win7_compatible and not any(arg == "-platform" or arg.startswith("-platform=") for arg in app_args):
        app_args.extend(["-platform", "windows:nodirectwrite"])

    app = Application(app_args)
    app.setup_app()
    
    from gui.interface.main_window import MainWindow

    app.window = MainWindow()
    app.process_pending_instance_activation()

    QTimer.singleShot(0, app.bootstrap_startup_tasks)

    exit_code = app.exec()

    # 事件循环退出时 aboutToQuit 已经触发，实例锁与数据库写入均已收尾，
    # 此处不再让解释器去清理那些可能仍在运行的线程对象
    shutdown_process(exit_code)

if __name__ == "__main__":
    _main()
