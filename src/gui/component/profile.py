from PySide6.QtGui import QColor, QPixmap

from qfluentwidgets import (
    AvatarWidget, BodyLabel, CaptionLabel, HyperlinkButton, FlyoutViewBase, MessageBox, isDarkTheme
)

from util.common.enum import ToastNotificationCategory
from util.common import signal_bus, config
from util.auth import user_manager

class ProfileCard(FlyoutViewBase):
    """
    展示用户信息的组件。
    """
    def __init__(self, parent = None):
        super().__init__(parent)

        self.main_window = parent

        self.init_UI()

    def init_UI(self):
        self.avatar = AvatarWidget(image = config.user_avatar_pixmap, parent = self)
        self.avatar.setRadius(24)

        self.uname_lab = BodyLabel(config.user_uname, parent = self)

        color = QColor(206, 206, 206) if isDarkTheme() else QColor(96, 96, 96)

        self.uid_lab = CaptionLabel(f"UID: {config.user_uid}", parent = self)
        self.uid_lab.setStyleSheet('QLabel{color: ' + color.name() + '}')

        self.logout_btn = HyperlinkButton(parent = self)
        self.logout_btn.setText(self.tr("Logout"))

        self.avatar.move(12, 10)
        self.uname_lab.move(74, 12)
        self.uid_lab.move(74, 31)
        self.logout_btn.move(62, 48)

        self.setFixedSize(250, 90)

        self.connect_signals()

    def connect_signals(self):
        self.logout_btn.clicked.connect(self.on_logout)

    def on_logout(self):
        self.close()

        dialog = MessageBox(self.tr("Log Out"), self.tr("Are you sure you want to log out? This will also clear locally stored cookies."), self.main_window)

        if dialog.exec():
            user_manager.logout()

            signal_bus.login.update_avatar.emit(QPixmap(":/bili23/image/noface.jpg"))
            signal_bus.toast.show.emit(ToastNotificationCategory.SUCCESS, "", self.tr("Successfully logged out"))

            # 注销后更新预览信息
            self.main_window.parse_interface.update_previewer_info()
        