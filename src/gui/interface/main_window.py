from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import Qt, QTimer

from qfluentwidgets import (
    MSFluentWindow, SystemThemeListener, NavigationItemPosition, InfoBar, InfoBarPosition, TeachingTip,
    TeachingTipTailPosition, Flyout, FlyoutAnimationType, FluentIcon
)

from gui.component.widget import NavigationLargeAvatarWidget
from gui.interface.download import DownloadInterface
from gui.interface.setting import SettingInterface
from gui.interface.parse import ParseInterface
from gui.component.profile import ProfileCard
from gui.dialog.login import LoginDialog
from gui.dialog.about import AboutDialog

from util.common.enum import ToastNotificationCategory
from util.common.signal_bus import signal_bus
from util.auth.cookie import CookieManager
from util.auth.user import UserManager
from util.common.config import config

class MainWindow(MSFluentWindow):
    def __init__(self):
        super().__init__()

        self.resize(950, 600)
        self.setWindowTitle("Bili23 Downloader")
        self.setWindowIcon(QIcon(":/bili23/icon/app.svg"))
        self.setObjectName("MainWindow")

        self.init_UI()

        self.init_utils()

        # 关闭云母特效，提升性能
        self.setMicaEffectEnabled(False)

        self.center_on_screen()

    def init_UI(self):
        self.parse_interface = ParseInterface(self)
        self.download_interface = DownloadInterface(self)
        self.setting_interface = SettingInterface(self)

        self.addSubInterface(self.parse_interface, FluentIcon.SEARCH, self.tr("Parse"), position = NavigationItemPosition.TOP)
        self.addSubInterface(self.download_interface, FluentIcon.DOWNLOAD, self.tr("Download"), position = NavigationItemPosition.TOP)

        self.avatar_widget = NavigationLargeAvatarWidget("", QPixmap(":/bili23/image/noface.jpg"), self)

        self.navigationInterface.addItem(
            "about",
            FluentIcon.INFO,
            self.tr("About"),
            onClick = self.on_about_click,
            selectable = False,
            position = NavigationItemPosition.TOP
        )

        self.navigationInterface.addWidget(
            "avatar",
            self.avatar_widget,
            onClick = self.on_avatar_click,
            position = NavigationItemPosition.BOTTOM
        )

        self.addSubInterface(self.setting_interface, FluentIcon.SETTING, self.tr("Settings"), position = NavigationItemPosition.BOTTOM)

        self.connect_signals()

    def connect_signals(self):
        signal_bus.toast.show.connect(self.show_toast_notification)

        signal_bus.login.update_avatar.connect(self.on_update_avatar)

    def init_utils(self):
        # 监听系统主题变化
        self.theme_listener = SystemThemeListener(self)
        self.theme_listener.start()

        self.user_manager = UserManager()
        self.user_manager.get_user_info()

        self.cookie_manager = CookieManager()

        if 1 == 0 and not config.get(config.is_login):
            QTimer.singleShot(300, self.show_teaching_tip)

    def closeEvent(self, e):
        self.theme_listener.terminate()
        self.theme_listener.deleteLater()

        super().closeEvent(e)

    def on_about_click(self):
        dialog = AboutDialog(self)
        dialog.exec()

    def on_avatar_click(self):
        if config.get(config.is_login):
            # 已登录，点击头像显示用户信息
            Flyout.make(
                view = ProfileCard(self.user_manager.logout, self),
                target = self.avatar_widget,
                parent = self,
                aniType = FlyoutAnimationType.SLIDE_RIGHT
            )
        else:
            # 未登录，点击头像显示登录界面
            dialog = LoginDialog(self)

            if dialog.exec():
                self.user_manager.get_user_info()

    def on_update_avatar(self, pixmap: QPixmap):
        self.avatar_widget.setAvatar(pixmap)

    def show_toast_notification(self, category: ToastNotificationCategory, title: str, content: str):
        match category:
            case ToastNotificationCategory.SUCCESS:
                func = InfoBar.success

            case ToastNotificationCategory.ERROR:
                func = InfoBar.error

            case ToastNotificationCategory.WARNING:
                func = InfoBar.warning

            case ToastNotificationCategory.INFO:
                func = InfoBar.info

        func(
            title = title,
            content = content,
            orient = Qt.Orientation.Horizontal,
            isClosable = False,
            duration = 3000,
            position = InfoBarPosition.TOP,
            parent = self
        )

    def show_teaching_tip(self):
        TeachingTip.create(
            target = self.avatar_widget,
            title = "登录",
            content = "点击头像登录账号",
            icon = FluentIcon.INFO,
            isClosable = True,
            duration = 10000,
            tailPosition = TeachingTipTailPosition.LEFT,
            parent = self
        )

    def center_on_screen(self):
        desktop = QApplication.screens()[0].availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w//2 - self.width()//2, h//2 - self.height()//2)
        self.show()

        QApplication.processEvents()
