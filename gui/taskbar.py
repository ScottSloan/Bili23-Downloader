import wx
import wx.adv

from utils.config import Config

class TaskBarIcon(wx.adv.TaskBarIcon):
    def __init__(self):
        wx.adv.TaskBarIcon.__init__(self, iconType = wx.adv.TBI_DEFAULT_TYPE)

        self.SetIcon(wx.Icon(Config.res_logo), "Bili23 Downloader")

        self.Bind(wx.EVT_MENU, self.on_Exit, id = 500)
    
    def CreatePopupMenu(self):
        menu = wx.Menu()
        menu.Append(500, "退出")

        return menu

    def Set_Title(self, title):
        self.SetIcon(wx.Icon(Config.res_logo), title)

    def on_Show(self, event):
        pass

    def on_Exit(self, event):
        wx.Exit()

class TaskBarProgress:
    def __init__(self, parent):
        pass