import wx

from gui.id import ID

class UserMenu(wx.Menu):
    def __init__(self):
        wx.Menu.__init__(self)

        self.Append(ID.REFRESH_MENU, "刷新(&R)")
        self.Append(ID.LOGOUT_MENU, "注销(&L)")
        self.AppendSeparator()
        self.Append(ID.SETTINGS_MENU, "设置(&S)")