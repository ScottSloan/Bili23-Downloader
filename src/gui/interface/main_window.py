from PySide6.QtWidgets import QApplication
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import Qt, QTimer

from qfluentwidgets import (
    MSFluentWindow, SystemThemeListener, NavigationItemPosition, InfoBar, InfoBarPosition, TeachingTip,
    TeachingTipTailPosition, Flyout, FlyoutAnimationType, FluentIcon, InfoBadge, MessageBox
)

from gui.component.widget import NavigationLargeAvatarWidget, FavoriteFlyoutMenu
from gui.interface import DownloadInterface, SettingInterface, ParseInterface
from gui.dialog.misc import AboutDialog, ExitDialog, TermsOfUseDialog
from gui.component import SystemTrayIcon, ProfileCard
from gui.dialog.update import UpdateDialog
from gui.dialog.login import LoginDialog

from util.common import signal_bus, config, Directory, ExtendedFluentIcon
from util.common.enum import ToastNotificationCategory, WhenClose
from util.auth import user_manager
from util.misc import Updater

class MainWindow(MSFluentWindow):
    def __init__(self):
        super().__init__()

        self.resize(950, 600)
        self.setWindowTitle("Bili23 Downloader")
        self.setWindowIcon(QIcon(":/bili23/icon/app.svg"))
        self.setObjectName("MainWindow")

        self.current_route_key = "ParseInterface"

        self.init_UI()

        self.init_utils()

        self.center_on_screen()

    def init_UI(self):
        self.parse_interface = ParseInterface(self)
        self.download_interface = DownloadInterface(self)
        self.setting_interface = SettingInterface(self)

        self.navigationInterface

        self.parse_btn = self.addSubInterface(self.parse_interface, FluentIcon.SEARCH, self.tr("Parser"), position = NavigationItemPosition.TOP)
        self.parse_btn.clicked.connect(lambda: self.update_route_key("ParseInterface"))

        self.download_btn = self.addSubInterface(self.download_interface, FluentIcon.DOWNLOAD, self.tr("Downloads"), position = NavigationItemPosition.TOP)
        self.download_btn.clicked.connect(lambda: self.update_route_key("DownloadInterface"))

        self.download_info_badge = InfoBadge.error("99+", parent = self, target = self.download_btn)
        self.download_info_badge.hide()

        self.favorite_widget = self.navigationInterface.addItem(
            "favorite",
            ExtendedFluentIcon.FAVORITE,
            self.tr("Favorites"),
            onClick = self.show_favorites_flyout_menu,
            selectable = True,
            position = NavigationItemPosition.TOP
        )

        self.about_widget = self.navigationInterface.addItem(
            "about",
            FluentIcon.INFO,
            self.tr("About"),
            onClick = self.on_about_click,
            selectable = False,
            position = NavigationItemPosition.TOP
        )

        self.avatar_widget = NavigationLargeAvatarWidget("", QPixmap(":/bili23/image/noface.jpg"), self)

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
        signal_bus.interface.mica_effect_changed.connect(self.setMicaEffectEnabled)

        signal_bus.parse.parse_url.connect(self.on_reparse_task)

    def init_utils(self):
        # 监听系统主题变化
        self.theme_listener = SystemThemeListener(self)
        self.theme_listener.start()

        self.setMicaEffectEnabled(config.get(config.mica_effect))

        self.updater = Updater()

        signal_bus.update.check.connect(self.updater.request_update)

        if not config.get(config.accepted_terms):
            QTimer.singleShot(300, self.show_terms_of_use)
        
        else:
            signal_bus.update.check.emit(False)

        QTimer.singleShot(300, self.check_download_path)
        QTimer.singleShot(300, self.check_ffmpeg)

        signal_bus.emit_pending_signals()

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
        if not config.get(config.is_login) or config.is_expired:
            # 未登录，点击头像显示登录界面
            dialog = LoginDialog(self)

            if dialog.exec():
                user_manager.get_user_info()
            
        else:
            # 已登录，点击头像显示用户信息
            Flyout.make(
                view = ProfileCard(self),
                target = self.avatar_widget,
                parent = self,
                aniType = FlyoutAnimationType.SLIDE_RIGHT
            )

    def on_update_avatar(self, pixmap: QPixmap):
        self.avatar_widget.setAvatar(pixmap)

    def on_reparse_task(self, url: str):
        if self.navigationInterface.currentItem().objectName() != "ParseInterface":
            self.navigationInterface.buttons()[0].click()  # 切换到解析界面

        self.parse_interface.reparse(url)

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

    def check_download_path(self):
        download_path = config.get(config.download_path)

        accessible = Directory.ensure_directory_accessible(download_path)

        if not accessible:
            signal_bus.toast.show_long_message.emit(
                self.tr("Download Directory Invalid"),
                self.tr("The current download directory is inaccessible or lacks write permissions. Please reset it.") + f"\n\n{download_path}"
            )

    def check_ffmpeg(self):
        if config.no_ffmpeg_available:
            signal_bus.toast.show_long_message.emit(
                self.tr("FFmpeg Not Found"),
                self.tr("No FFmpeg executable found. Please ensure FFmpeg is installed and configured correctly.")
            )

    def show_favorites_flyout_menu(self):
        if not config.get(config.is_login) or config.is_expired:
            dialog = MessageBox(
                title = self.tr("Login Required"),
                content = self.tr("Please log in to your account first."),
                parent = self
            )
            dialog.hideCancelButton()
            dialog.exec()

            self.reset_route_key()

            return

        menu = FavoriteFlyoutMenu(self)

        flyout = Flyout(menu, self)
        flyout.resize(flyout.sizeHint())

        w = flyout.make(menu, self.about_widget, self, aniType = FlyoutAnimationType.SLIDE_RIGHT, isDeleteOnClose = True)
        menu.closed.connect(w.close)

        flyout.closed.connect(self.reset_route_key)

    def update_route_key(self, key: str):
        self.current_route_key = key

    def reset_route_key(self):
        self.navigationInterface.setCurrentItem(self.current_route_key)