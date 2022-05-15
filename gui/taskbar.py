import wx
import os
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

    TBPF_NOPROGRESS = 0
    TBPF_INDETERMINATE = 0x1
    TBPF_NORMAL = 0x2
    TBPF_ERROR = 0x4
    TBPF_PAUSED = 0x8

    def __init__(self):
        if not Config.PLATFORM.startswith("Windows"): return

        from comtypes import client
        client.GetModule(os.path.join(os.getcwd(), "taskbar.tlb"))

        import comtypes.gen.TaskbarLib as tbl
        self.taskbar = client.CreateObject("{56FDF344-FD6D-11d0-958A-006097C9A090}", interface = tbl.ITaskbarList3)

        self.taskbar.HrInit()
    
    def Bind(self, hwnd):
        self.hwnd = hwnd
    
    def SetProgressState(self, state):
        self.taskbar.SetProgressState(self.hwnd, state)

    def SetProgressValue(self, value):
        self.taskbar.SetProgressValue(self.hwnd, value, 100)
