from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import Qt, QTimer

from qfluentwidgets import (
    MSFluentWindow, SystemThemeListener, NavigationItemPosition, InfoBar, InfoBarPosition, TeachingTip,
    TeachingTipTailPosition, Flyout, FlyoutAnimationType, FluentIcon, InfoBadge
)

from gui.interface import DownloadInterface, SettingInterface, ParseInterface
from gui.dialog.misc import AboutDialog, ExitDialog, TermsOfUseDialog
from gui.component.widget import NavigationLargeAvatarWidget
from gui.component import SystemTrayIcon, ProfileCard
from gui.dialog.update import UpdateDialog
from gui.dialog.login import LoginDialog

from util.common.enum import ToastNotificationCategory, WhenClose
from util.auth import CookieManager, UserManager
from util.common import signal_bus, config
from util.misc import Updater

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
        self.download_btn = self.addSubInterface(self.download_interface, FluentIcon.DOWNLOAD, self.tr("Download"), position = NavigationItemPosition.TOP)

        self.download_info_badge = InfoBadge.error("99+", parent = self, target = self.download_btn)
        self.download_info_badge.hide()

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

        self.system_tray_icon = SystemTrayIcon(self)
        self.system_tray_icon.show()

        self.connect_signals()

    def connect_signals(self):
        signal_bus.toast.show.connect(self.show_toast_notification)
        signal_bus.toast.show_long_message.connect(self.show_toast_notification_long_message)
        signal_bus.toast.sys_show.connect(self.system_tray_icon.show_message)

        signal_bus.login.update_avatar.connect(self.on_update_avatar)

        signal_bus.download.update_downloading_count.connect(self.update_download_btn_badge_info)

        signal_bus.update.show_dialog.connect(self.show_update_dialog)

    def init_utils(self):
        # 监听系统主题变化
        self.theme_listener = SystemThemeListener(self)
        self.theme_listener.start()

        self.user_manager = UserManager()
        self.user_manager.get_user_info()

        self.cookie_manager = CookieManager()

        self.updater = Updater()
        signal_bus.update.check.connect(self.updater.request_update)

        # if 1 == 0 and not config.get(config.is_login):
        #     QTimer.singleShot(300, self.show_teaching_tip)

        if not config.get(config.accepted_terms):
            QTimer.singleShot(300, self.show_terms_of_use)
        
        else:
            signal_bus.update.check.emit(False)

    def closeEvent(self, e):
        if not self.on_close():
            e.ignore()
            return
        
        self.theme_listener.terminate()
        self.theme_listener.deleteLater()

        super().closeEvent(e)

    def on_close(self):
        match config.get(config.when_close_window):
            case WhenClose.MINIMIZE:
                self.hide()

                return False
            
            case WhenClose.ALWAYS_ASK:
                dialog = ExitDialog(self)

                if dialog.exec():
                    if dialog.exit_radio.isChecked():
                        return True
                    
                    else:
                        self.hide()

                        return False

                else:
                    return False
                
            case WhenClose.EXIT:
                return True

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

    def show_toast_notification_long_message(self, title: str, content: str):
        InfoBar.error(
            title = title,
            content = content,
            orient = Qt.Orientation.Vertical,
            isClosable = True,
            duration = -1,
            position = InfoBarPosition.BOTTOM_RIGHT,
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

    def show_terms_of_use(self):
        dialog = TermsOfUseDialog(self)

        if not dialog.exec():
            # 用户不接受使用协议，关闭程序
            self.close()

        # 许可协议优先级最高，之后再显示更新等提示
        signal_bus.update.check.emit(False)

    def show_update_dialog(self, info: dict):
        dialog = UpdateDialog(info, self)
        dialog.exec()

    def center_on_screen(self):
        desktop = QApplication.screens()[0].availableGeometry()
        w, h = desktop.width(), desktop.height()
        self.move(w//2 - self.width()//2, h//2 - self.height()//2)
        self.show()

        QApplication.processEvents()

    def update_download_btn_badge_info(self, count: int):
        if self.download_info_badge.isHidden():
            self.download_info_badge.show()

        if count > 99:
            self.download_info_badge.setText("99+")
        elif count == 0:
            self.download_info_badge.hide()
            return
        else:
            self.download_info_badge.setText(str(count))

        self.download_info_badge.adjustSize()

        self.download_info_badge.move(self.download_btn.width() - 4, 111)
