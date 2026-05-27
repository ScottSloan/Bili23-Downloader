from PySide6.QtCore import QStandardPaths

from logging.handlers import TimedRotatingFileHandler
from pathlib import Path
import logging
import sys
import os

# --------- Logging Configuration ---------

appdata_path = QStandardPaths.writableLocation(QStandardPaths.StandardLocation.AppDataLocation)

log_path = Path(appdata_path) / "Bili23 Downloader" / "logs" / "app.log"
log_path.parent.mkdir(parents = True, exist_ok = True)

logging.basicConfig(
    level = logging.INFO,
    format = "[%(asctime)s] - %(name)s - %(levelname)s: %(message)s",
    datefmt = "%Y-%m-%d %H:%M:%S",
    handlers = [
        logging.StreamHandler(sys.stdout),
        TimedRotatingFileHandler(log_path, when = "midnight", interval = 1, backupCount = 15, encoding = "utf-8")
    ]
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

logger = logging.getLogger(__name__)

class Application(QApplication):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

        self.window = None
        self.instance_server: QLocalServer = None
        self.pending_instance_activation = False
        self.aboutToQuit.connect(self.cleanup_instance_state)

        self.init_single_instance()

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

            if self.force_take_over_existing_instance():
                self.init_instance_server()
                return

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

    def force_take_over_existing_instance(self) -> bool:
        import psutil
        
        try:
            lock_pid, _, _ = self.instance_lock.getLockInfo()
        except Exception as exc:
            logger.warning("无法读取实例锁信息: %s", exc)
            return False

        if not lock_pid:
            logger.warning("实例锁中没有有效的进程信息，无法强制接管")
            return False

        try:
            process = psutil.Process(lock_pid)
        except psutil.NoSuchProcess:
            logger.warning("锁对应进程已不存在，尝试重新获取实例锁")
            self.instance_lock.removeStaleLockFile()

            return self.instance_lock.tryLock(0)

        children = process.children(recursive = True)

        for child in children:
            try:
                child.terminate()
            except psutil.Error:
                pass

        try:
            process.terminate()
        except psutil.Error:
            pass

        _, alive = psutil.wait_procs([process, *children], timeout = 5)

        for proc in alive:
            try:
                proc.kill()
            except psutil.Error:
                pass

        if alive:
            psutil.wait_procs(alive, timeout = 2)

        self.instance_lock.removeStaleLockFile()

        if self.instance_lock.tryLock(0):
            logger.warning("原实例无法唤醒，已结束旧进程并接管实例")
            return True

        logger.warning("已结束旧进程，但仍无法重新获取实例锁")
        return False

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

        cookie_manager.init_cookie_info()
        user_manager.init_user_info()

def _main():
    scaling_value = config.get(config.display_scaling).value

    if scaling_value != "Auto":
        os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
        os.environ["QT_SCALE_FACTOR"] = scaling_value

    app = Application(sys.argv)
    app.setup_app()
    
    from gui.interface.main_window import MainWindow

    app.window = MainWindow()
    app.process_pending_instance_activation()

    QTimer.singleShot(0, app.bootstrap_startup_tasks)

    app.exec()

if __name__ == "__main__":
    _main()
