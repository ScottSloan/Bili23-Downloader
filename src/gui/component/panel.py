import wx

from utils.common.enums import Platform
from utils.config import Config

class Panel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

    def get_scaled_size(self, size: tuple):
        match Platform(Config.Sys.platform):
            case Platform.Windows:
                return self.FromDIP(size)
            
            case Platform.Linux | Platform.macOS:
                return wx.DefaultSize
    
    def set_dark_mode(self):
        if not Config.Sys.dark_mode:
            self.SetBackgroundColour("white")