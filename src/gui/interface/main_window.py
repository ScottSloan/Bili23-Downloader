from PySide6.QtWidgets import QApplication, QWidget
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtCore import Qt, QTimer

from qfluentwidgets import (
    MSFluentWindow, SystemThemeListener, NavigationItemPosition, FluentIcon, InfoBadge, qrouter, setTheme
)

from util.common.enum import ToastNotificationCategory, WhenClose
from util.common.signal_bus import signal_bus, config
from util.common.icon import ExtendedFluentIcon
from util.common.config import config

import logging

logger = logging.getLogger(__name__)

class MainWindowBase:
    def run_post_terms_checks(self: "MainWindow") -> None:
        signal_bus.update.check.emit(False)

        if not config.get(config.tutorial_dialog_shown):
            self.show_tutorial_dialog()

            config.set(config.tutorial_dialog_shown, True)

        if not config.get(config.select_area_dialog_shown):
            self.show_select_area_dialog()

            config.set(config.select_area_dialog_shown, True)

        if not config.get(config.is_login):
            self.show_login_teaching_tip()

        QTimer.singleShot(0, self.check_download_path)
        QTimer.singleShot(0, self.check_ffmpeg)

        signal_bus.emit_pending_signals()

    def _get_toast_function(self, category: ToastNotificationCategory):
        from gui.component.widget.info_bar import InfoBar

        match category:
            case ToastNotificationCategory.SUCCESS:
                func = InfoBar.success

            case ToastNotificationCategory.ERROR:
                func = InfoBar.error

            case ToastNotificationCategory.WARNING:
                func = InfoBar.warning

            case ToastNotificationCategory.INFO:
                func = InfoBar.info

        return func

    def show_toast_notification(self, category: ToastNotificationCategory, title: str, content: str):
        from gui.component.widget.info_bar import InfoBarPosition

        func = self._get_toast_function(category)

        func(
            title = title,
            content = content,
            orient = Qt.Orientation.Horizontal,
            isClosable = False,
            duration = 3000,
            position = InfoBarPosition.TOP,
            parent = self
        )

    def show_toast_notification_long_message(self, category: ToastNotificationCategory, title: str, content: str):
        from gui.component.widget.info_bar import InfoBarPosition

        func = self._get_toast_function(category)

        func(
            title = title,
            content = content,
            orient = Qt.Orientation.Vertical,
            isClosable = True,
            duration = 5000,
            position = InfoBarPosition.BOTTOM_RIGHT,
            parent = self,
            contentMaxHeight = 200
        )

    def show_tutorial_dialog(self):
        # 询问用户是否首次使用，建议用户查看文档，充分利用程序功能
        from qfluentwidgets import MessageBox

        dialog = MessageBox(
            title = self.tr("Welcome to Bili23 Downloader"),
            content = self.tr("It is recommended to read the user guide and FAQs when using for the first time, to help you get started quickly and make full use of all features."),
            parent = self
        )
        dialog.yesButton.setText(self.tr("View"))
        dialog.cancelButton.setText(self.tr("Skip"))

        if dialog.exec():
            import webbrowser

            webbrowser.open("https://bili23.scott-sloan.cn/doc/introduction.html")

    def show_login_teaching_tip(self: "MainWindow"):
        from qfluentwidgets import TeachingTip, TeachingTipTailPosition

        TeachingTip.create(
            target = self.avatar_widget,
            title = self.tr("Log in to your account"),
            content = self.tr("Click the avatar to log in to your Bilibili account. \nDownload functionality will be limited if you're not logged in."),
            icon = FluentIcon.INFO,
            isClosable = True,
            duration = -1,
            tailPosition = TeachingTipTailPosition.LEFT,
            parent = self
        )

    def show_terms_of_use(self):
        from ..dialog.main_window.terms import TermsOfUseDialog

        dialog = TermsOfUseDialog(self)

        if not dialog.exec():
            # 用户不接受使用协议，关闭程序
            self.close()

            logger.warning("用户未接受使用协议，程序已关闭")

            return False

        self.run_post_terms_checks()

        return True
    
    def show_update_dialog(self, info: dict):
        from ..dialog.update import UpdateDialog

        dialog = UpdateDialog(info, self)
        dialog.exec()

    def show_select_area_dialog(self):
        from ..dialog.setting.select_area import SelectAreaDialog

        dialog = SelectAreaDialog(self)
        dialog.exec()

    def center_on_screen(self: "MainWindow", show = True):
        from PySide6.QtWidgets import QApplication

        desktop = QApplication.screens()[0].availableGeometry()
        w, h = desktop.width(), desktop.height()

        self.move(w // 2 - self.width() // 2, h // 2 - self.height() // 2)

        if show:
            self.initialized = True
            self.show()

    def update_download_btn_badge_info(self: "MainWindow", count: int):
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
        from util.common.io.directory import Directory

        download_path = config.get(config.download_path)

        accessible = Directory.ensure_directory_accessible(download_path)

        if not accessible:
            signal_bus.toast.show_long_message.emit(
                ToastNotificationCategory.ERROR,
                self.tr("Download Directory Invalid"),
                self.tr("The current download directory is inaccessible or lacks write permissions. Please reset it.") + f"\n\n{download_path}"
            )

            logger.error("下载目录不可访问或缺少写入权限：%s", download_path)

    def check_ffmpeg(self):
        if config.no_ffmpeg_available:
            signal_bus.toast.show_long_message.emit(
                ToastNotificationCategory.ERROR,
                self.tr("FFmpeg Not Found"),
                self.tr("No FFmpeg executable found. Please ensure FFmpeg is installed and configured correctly.")
            )

    def show_favorites_flyout_menu(self: "MainWindow"):
        from qfluentwidgets import FlyoutAnimationType, FlyoutAnimationManager, MessageBox
        from PySide6.QtCore import QPoint

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
        
        if not self.flyout_initialized:
            self.flyout_initialized = True

            # 首次显示时加载数据
            self.flyout_widget.init_flyout()

        self.flyout_widget.adjust_list_widget_width(self.size())
        
        manager = FlyoutAnimationManager.make(
            aniType = FlyoutAnimationType.SLIDE_RIGHT,
            flyout = self.flyout
        )
        target_pos: QPoint = manager.position(self.about_btn)
        target_pos.setY(max(target_pos.y() + 20, 40))

        self.flyout.exec(
            target_pos,
            FlyoutAnimationType.SLIDE_RIGHT
        )

    def update_route_key(self, key: str):
        self.current_route_key = key

    def reset_route_key(self: "MainWindow"):
        self.navigationInterface.setCurrentItem(self.current_route_key)

    def _activate_window(self: "MainWindow"):
        if not self.initialized:
            self.resize(950, 600)
            self.center_on_screen(show = True)

        if self.isMinimized():
            self.showNormal()
        else:
            self.show()

        self.raise_()
        self.activateWindow()
    
    def _addSubInterface(self: "MainWindow", interface: QWidget):
        interface.setProperty("isStackedTransparent", False)
        self.stackedWidget.addWidget(interface)

        routeKey = interface.objectName()

        self.navigationInterface.items[routeKey].clicked.connect(lambda: self.switchTo(interface))
        
        if self.stackedWidget.count() == 1:
            self.stackedWidget.currentChanged.connect(self._onCurrentInterfaceChanged)
            self.navigationInterface.setCurrentItem(routeKey)
            qrouter.setDefaultRouteKey(self.stackedWidget, routeKey)

        self._updateStackedBackground()

class MainWindow(MainWindowBase, MSFluentWindow):
    def __init__(self):
        super().__init__()

        self.resize(950, 600)
        self.setMinimumSize(950, 600)
        self.setWindowTitle("Bili23 Downloader")
        self.setWindowIcon(QIcon(":/bili23/icon/app.svg"))
        self.setObjectName("MainWindow")

        self.current_route_key = "ParseInterface"
        self.flyout_initialized = False
        self.initialized = False

        # 由托盘菜单、强制更新等入口置位，令 on_close 跳过"关闭时的行为"设置直接退出
        self.force_close = False

        # 设置界面构造耗时约 0.5 秒，且多数启动过程中并不会用到，推迟到首次进入设置页时再创建
        self.setting_interface = None

        self.init_UI()

        self.center_on_screen(not config.get(config.silent_start))

        # 设置鼠标指针为等待状态，直到工具初始化完成
        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)

        self.setMicaEffectEnabled(config.get(config.mica_effect))

        QTimer.singleShot(0, self.init_utils)
        
    def init_UI(self):
        from .parse import ParseInterface
        from gui.component.widget.avatar import NavigationLargeAvatarWidget

        self.parse_interface = ParseInterface(self)
        self.parse_btn = self.addSubInterface(self.parse_interface, FluentIcon.SEARCH, self.tr("Parser"), position = NavigationItemPosition.TOP)

        # 先创建导航栏按钮，后续再添加界面
        self.download_btn = self.navigationInterface.addItem(
            "DownloadInterface",
            FluentIcon.DOWNLOAD,
            self.tr("Downloads"),
            selectable = True,
            position = NavigationItemPosition.TOP
        )

        self.download_info_badge = InfoBadge.error("99+", parent = self, target = self.download_btn)
        self.download_info_badge.hide()

        self.favorite_btn = self.navigationInterface.addItem(
            "favorite",
            ExtendedFluentIcon.FAVORITE,
            self.tr("Favorites"),
            onClick = self.show_favorites_flyout_menu,
            selectable = True,
            position = NavigationItemPosition.TOP
        )

        self.about_btn = self.navigationInterface.addItem(
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

        self.setting_btn = self.navigationInterface.addItem(
            "SettingInterface",
            FluentIcon.SETTING,
            self.tr("Settings"),
            selectable = True,
            position = NavigationItemPosition.BOTTOM
        )

        self.connect_signals()

        if config.get(config.stay_on_top):
            self.setStayOnTop(True)

    def init_deferred_ui(self):
        from gui.component.widget.flyout import FavoriteFlyoutWidget
        from gui.component.sys_tray import SystemTrayIcon

        from qfluentwidgets import Flyout

        from .download import DownloadInterface

        self.download_interface = DownloadInterface(self)

        self._addSubInterface(self.download_interface)

        self.system_tray_icon = SystemTrayIcon(self)
        self.system_tray_icon.show()

        signal_bus.toast.sys_show.connect(self.system_tray_icon.show_message)

        self.flyout_widget = FavoriteFlyoutWidget(self)

        self.flyout = Flyout.make(
            view = self.flyout_widget,
            parent = self,
            isDeleteOnClose = False
        )

        self.flyout_widget.closed.connect(self.flyout.fadeOut)
        self.flyout.closed.connect(self.reset_route_key)

    def ensure_setting_interface(self):
        # 首次进入设置页时才构造设置界面
        if self.setting_interface is not None:
            return

        from .setting import SettingInterface

        self.setting_interface = SettingInterface(self)

        self._addSubInterface(self.setting_interface)

        # _addSubInterface 中建立的 clicked -> switchTo 连接对本次点击不生效，此处手动切换一次
        self.switchTo(self.setting_interface)

    def connect_signals(self):
        # 跟随系统主题切换。该连接原先建立在设置界面中，设置界面改为懒加载后需要提前到此处
        config.themeChanged.connect(setTheme)

        signal_bus.toast.show.connect(self.show_toast_notification)
        signal_bus.toast.show_long_message.connect(self.show_toast_notification_long_message)

        signal_bus.login.update_avatar.connect(self.on_update_avatar)
        signal_bus.download.update_downloading_count.connect(self.update_download_btn_badge_info)
        signal_bus.update.show_dialog.connect(self.show_update_dialog)
        signal_bus.interface.mica_effect_changed.connect(self.setMicaEffectEnabled)

        signal_bus.parse.parse_url.connect(self.on_reparse_task)

        self.parse_btn.clicked.connect(lambda: self.update_route_key("ParseInterface"))
        self.download_btn.clicked.connect(lambda: self.update_route_key("DownloadInterface"))
        self.setting_btn.clicked.connect(lambda: self.update_route_key("SettingInterface"))
        self.setting_btn.clicked.connect(self.ensure_setting_interface)

    def init_utils(self):
        QApplication.processEvents()

        self.init_deferred_ui()

        from util.ffmpeg import init_ffmpeg
        from util.misc.update import Updater

        # 探测 FFmpeg 涉及磁盘 IO，放在首屏之后执行，check_ffmpeg 依赖其结果
        init_ffmpeg()

        # 监听系统主题变化
        self.theme_listener = SystemThemeListener(self)
        self.theme_listener.start()

        self.updater = Updater(self)

        signal_bus.update.check.connect(self.updater.request_update)

        # 初始化完成，恢复鼠标指针
        QApplication.restoreOverrideCursor()

        if not config.get(config.accepted_terms):
            QTimer.singleShot(0, self.show_terms_of_use)

            return

        self.run_post_terms_checks()

    def closeEvent(self, e):
        from util.download.downloader.manager import downloader_manager
        from util.download.task.manager import task_manager
        from util.thread.async_ import AsyncTask

        if not self.on_close():
            e.ignore()
            return

        # 隐藏窗口，给用户反馈正在关闭的状态，避免长时间无响应的感觉
        self.hide()

        # 先让后台工作真正停下来，再去等线程退出。分片线程阻塞在 socket 读上，
        # 不关掉会话的话，safe_quit 的等待预算会全部耗在读超时上
        downloader_manager.shutdown()

        AsyncTask.safe_quit()

        # 任务状态是异步写入的，退出前等待队列中的写入落盘
        task_manager.shutdown()

        # 主题监听线程阻塞在系统的注册表变更通知上，quit() 唤不醒它。
        # 这里既不强杀也不销毁：terminate() 在 Windows 上会在任意指令处杀死线程，
        # 若当时正持有 CRT 堆锁，之后任何一次 free 都会崩溃；而销毁一个仍在运行的
        # QThread 会让 Qt 直接 qFatal。交给 shutdown_process() 随进程一起回收。
        #
        # 强制更新对话框可能赶在 init_utils 完成之前就要求退出，此时监听器尚未创建
        theme_listener = getattr(self, "theme_listener", None)

        if theme_listener is not None and theme_listener.isRunning():
            theme_listener.quit()
            theme_listener.wait(500)

        super().closeEvent(e)

    def resizeEvent(self, e):
        if hasattr(self, "parse_interface"):
            self.parse_interface.adjust_column_width()

        return super().resizeEvent(e)

    def request_exit(self):
        """
        供托盘菜单、强制更新等入口调用，无条件退出程序

        这些入口以前直接 sys.exit()，绕开了 closeEvent 里的收尾工作：
        下载任务不会停止、数据库写入队列不会落盘，而且解释器随后清理全局变量时
        会析构仍在运行的 QThread，把退出变成崩溃。
        """
        self.force_close = True

        self.close()

    def on_close(self):
        if self.force_close:
            return True

        match config.get(config.when_close_window):
            case WhenClose.MINIMIZE:
                self.hide()

                return False
            
            case WhenClose.ALWAYS_ASK:
                from ..dialog.main_window.exit import ExitDialog

                dialog = ExitDialog(self)

                if dialog.exec():
                    if dialog.exit_checked:
                        return True
                    
                    else:
                        self.hide()

                        return False

                else:
                    return False
                
            case WhenClose.EXIT:
                return True

    def on_about_click(self):
        from ..dialog.main_window.about import AboutDialog

        dialog = AboutDialog(self)
        dialog.exec()

    def on_avatar_click(self):
        if not config.get(config.is_login) or config.is_expired:
            # 未登录，点击头像显示登录界面
            from ..dialog.login import LoginDialog
            from util.auth.user import user_manager

            dialog = LoginDialog(self)

            if dialog.exec():
                user_manager.get_user_info()
        else:
            # 已登录，点击头像显示用户信息
            from ..component.profile import ProfileCard
            from qfluentwidgets import Flyout, FlyoutAnimationType

            Flyout.make(
                view = ProfileCard(self),
                target = self.avatar_widget,
                parent = self,
                aniType = FlyoutAnimationType.SLIDE_RIGHT
            )

    def on_update_avatar(self, pixmap: QPixmap | bytes):
        if isinstance(pixmap, bytes):
            avatar_pixmap = QPixmap()
            avatar_pixmap.loadFromData(pixmap)

            pixmap = avatar_pixmap
            config.user_avatar_pixmap = avatar_pixmap

        self.avatar_widget.setAvatar(pixmap)

    def on_reparse_task(self, url: str):
        if self.navigationInterface.currentItem().objectName() != "ParseInterface":
            self.navigationInterface.buttons()[0].click()  # 切换到解析界面

        self.parse_interface.reparse(url)
