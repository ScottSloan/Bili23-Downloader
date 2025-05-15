import wx
import wx.adv

from utils.common.icon_v3 import Icon, IconID
from utils.config import Config

class TaskBarIcon(wx.adv.TaskBarIcon):
    def __init__(self, frame: wx.Frame):
        self.frame = frame

        wx.adv.TaskBarIcon.__init__(self)

        self.SetIcon(wx.Icon(Icon.get_icon_bitmap(IconID.APP_ICON_SMALL)), Config.APP.name)

        self.init_id()

        self.Bind_EVT()

    def CreatePopupMenu(self):
        menu = wx.Menu()

        main_menuitem = wx.MenuItem(menu, self.ID_MAIN_MENU, "主界面(&M)")
        download_menuitem = wx.MenuItem(menu, self.ID_DOWNLOAD_MENU, "下载管理(&D)")
        exit_menuitem = wx.MenuItem(menu, self.ID_EXIT_MENU, "退出(&X)")

        menu.Append(main_menuitem)
        menu.Append(download_menuitem)
        menu.AppendSeparator()
        menu.Append(exit_menuitem)

        return menu
    
    def init_id(self):
        self.ID_MAIN_MENU = wx.NewIdRef()
        self.ID_DOWNLOAD_MENU = wx.NewIdRef()
        self.ID_EXIT_MENU = wx.NewIdRef()

    def Bind_EVT(self):
        self.Bind(wx.EVT_MENU, self.onMenuEVT)

    def onMenuEVT(self, event):
        match event.GetId():
            case self.ID_MAIN_MENU:
                self.switch_window(self.frame)

            case self.ID_DOWNLOAD_MENU:
                self.switch_window(self.frame.download_window)

            case self.ID_EXIT_MENU:
                wx.Exit()
    
    def switch_window(self, frame: wx.Frame):
        if frame.IsIconized():
            frame.Iconize(False)
        
        elif not frame.IsShown():
            frame.Show()
            frame.CenterOnParent()

        frame.Raise()
