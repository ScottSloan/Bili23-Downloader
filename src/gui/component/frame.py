import wx

from utils.common.icon_v3 import Icon, IconID
from utils.common.enums import Platform
from utils.config import Config

class Frame(wx.Frame):
    def __init__(self, parent, title, style = wx.DEFAULT_FRAME_STYLE):
        wx.Frame.__init__(self, parent, -1, title, style = style)

        self.SetIcon(wx.Icon(Icon.get_icon_bitmap(IconID.APP_ICON_SMALL)))

    def get_scaled_size(self, size: tuple):
        match Platform(Config.Sys.platform):
            case Platform.Windows:
                return self.FromDIP(size)
            
            case Platform.Linux | Platform.macOS:
                return wx.DefaultSize
