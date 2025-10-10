import wx
import gettext

from gui.id import ID

_ = gettext.gettext

class UserMenu(wx.Menu):
    def __init__(self):
        wx.Menu.__init__(self)

        self.Append(ID.REFRESH_MENU, _("刷新(&R)"))
        self.Append(ID.LOGOUT_MENU, _("注销(&L)"))
        self.AppendSeparator()
        self.Append(ID.SETTINGS_MENU, _("设置(&S)"))