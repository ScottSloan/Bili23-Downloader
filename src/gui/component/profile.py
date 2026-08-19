from PySide6.QtGui import QPixmap

from qfluentwidgets import (
    AvatarWidget, BodyLabel, HyperlinkButton, FlyoutViewBase, MessageBox
)

from .widget.label import TipCaptionLabel

from util.common.enum import ToastNotificationCategory
from util.common.signal_bus  import signal_bus
from util.common.config import config
from util.auth.user import user_manager

import logging

logger = logging.getLogger(__name__)

class ProfileCard(FlyoutViewBase):
    """
    展示用户信息的组件。
    """
    def __init__(self, parent = None):
        super().__init__(parent)

        self.main_window = parent

        self.init_UI()

    def init_UI(self):
        # 头像请求失败时 user_avatar_pixmap 会保持默认的 None，而 AvatarWidget 的构造函数是
        # singledispatchmethod，None 匹配不到任何重载，会落到只接受 parent 的基础实现上并抛
        # TypeError。异常在 Qt 槽里被吞掉，表现为点击头像毫无反应，因此这里必须兜底
        avatar_pixmap = config.user_avatar_pixmap

        if avatar_pixmap is None or avatar_pixmap.isNull():
            avatar_pixmap = QPixmap(":/bili23/image/noface.jpg")

        self.avatar = AvatarWidget(image = avatar_pixmap, parent = self)
        self.avatar.setRadius(24)

        self.uname_lab = BodyLabel(config.user_uname, parent = self)

        self.uid_lab = TipCaptionLabel(f"UID: {config.user_uid}", parent = self)

        self.logout_btn = HyperlinkButton(parent = self)
        self.logout_btn.setText(self.tr("Logout"))

        self.open_profile_btn = HyperlinkButton(parent = self)
        self.open_profile_btn.setText(self.tr("Profile"))

        self.avatar.move(12, 10)
        self.uname_lab.move(74, 12)
        self.uid_lab.move(74, 31)
        self.open_profile_btn.move(62, 48)
        self.logout_btn.move(150, 48)

        self.setFixedSize(260, 90)

        self.connect_signals()

    def connect_signals(self):
        self.logout_btn.clicked.connect(self.on_logout)
        self.open_profile_btn.clicked.connect(self.on_open_profile)

    def on_logout(self):
        self.close()

        dialog = MessageBox(self.tr("Log Out"), self.tr("Are you sure you want to log out? This will also clear locally stored cookies."), self.main_window)

        if dialog.exec():
            user_manager.logout()

            signal_bus.login.update_avatar.emit(QPixmap(":/bili23/image/noface.jpg"))
            signal_bus.toast.show.emit(ToastNotificationCategory.SUCCESS, "", self.tr("Successfully logged out"))

            # 注销后更新预览信息
            self.main_window.parse_interface.update_previewer_info()

            logger.info("用户已注销登录")

    def on_open_profile(self):
        import webbrowser

        url = "https://space.bilibili.com/{uid}".format(uid = config.user_uid)

        webbrowser.open(url)
