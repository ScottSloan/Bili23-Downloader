import wx

from gui.id import ID

class URLMenu(wx.Menu):
    def __init__(self):
        wx.Menu.__init__(self)

        self.Append(ID.SUPPORTTED_URL_MENU, "支持解析的链接(&U)")
        #self.AppendSeparator()

        #history_menu_item = wx.MenuItem(self, ID.HISTORY_MENU, "历史记录(&H)")
        #history_menu_item.Enable(False)

        #self.Append(history_menu_item)