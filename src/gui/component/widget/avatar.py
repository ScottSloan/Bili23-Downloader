from qfluentwidgets import NavigationAvatarWidget

class NavigationLargeAvatarWidget(NavigationAvatarWidget):
    """
    原 NavigationAvatarWidget 只能搭配 FluentWindow 的小尺寸导航栏使用，
    因此创建了 NavigationLargeAvatarWidget 来适配 MSFluentWindow 的大尺寸导航栏。
    """
    def __init__(self, name, avatar = None, parent = None):
        super().__init__(name, avatar, parent)

        self.setFixedSize(64, 64)
        self.avatar.setRadius(19)

        self._center_avatar()

    def _center_avatar(self):
        # 将头像固定在组件顶部中央
        avatar_size = self.avatar.size()

        x = (self.width() - avatar_size.width()) // 2
        y = (self.height() - avatar_size.height()) // 2

        self.avatar.move(x, y)

    def setAvatar(self, avatar):
        super().setAvatar(avatar)

        self.avatar.setRadius(19)
        self._center_avatar()
