import wx

from utils.config import Config
from utils.common.enums import Platform

class Dialog(wx.Dialog):
    def __init__(self, parent, title):
        wx.Dialog.__init__(self, parent, -1, title)
        
        self.Bind(wx.EVT_CLOSE, self.onCloseEVT)

    def get_scaled_size(self, size: tuple):
        match Platform(Config.Sys.platform):
            case Platform.Windows:
                return self.FromDIP(size)
            
            case Platform.Linux | Platform.macOS:
                return wx.DefaultSize
    
    def set_dark_mode(self):
        if not Config.Sys.dark_mode:
            self.SetBackgroundColour("white")

    def onCloseEVT(self, event: wx.CloseEvent):
        match Platform(Config.Sys.platform):
            case Platform.Windows | Platform.Linux:
                self.Destroy()

            case Platform.macOS:
                event.Skip()
