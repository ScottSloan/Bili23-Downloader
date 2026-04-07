from PySide6.QtCore import QStandardPaths

from logging.handlers import TimedRotatingFileHandler
from multiprocessing import freeze_support
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

from PySide6.QtCore import Qt, QLocale, QTranslator
from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QFont

from util.auth import user_manager, cookie_manager
from qfluentwidgets import FluentTranslator
from util.common import config
import res.resources_rc

from gui.interface.main_window import MainWindow

class Application(QApplication):
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)

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

def main():
    scaling_value = config.get(config.scaling).value

    if scaling_value != "Auto":
        os.environ["QT_ENABLE_HIGHDPI_SCALING"] = "0"
        os.environ["QT_SCALE_FACTOR"] = scaling_value

    app = Application(sys.argv)
    app.setup_app()
    
    # 初始化登录状态等用户信息
    cookie_manager.init_cookie_info()
    user_manager.init_user_info()

    main_window = MainWindow()
    main_window.show()

    app.exec()

if __name__ == "__main__":
    freeze_support()
    
    main()
