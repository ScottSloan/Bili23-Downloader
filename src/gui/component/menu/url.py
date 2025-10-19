import wx
import gettext

from gui.id import ID

_ = gettext.gettext

class URLMenu(wx.Menu):
    def __init__(self):
        wx.Menu.__init__(self)

        self.Append(ID.SUPPORTTED_URL_MENU, _("支持解析的链接(&U)"))
        self.AppendSeparator()

        history_menu_item = wx.MenuItem(self, ID.HISTORY_MENU, "历史记录(&H)")

        self.Append(history_menu_item)

        self.Enable(ID.HISTORY_MENU, False)