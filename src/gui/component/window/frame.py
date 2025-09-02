import wx

from utils.common.style.icon_v4 import Icon, IconID
from utils.common.enums import Platform
from utils.config import Config

class Frame(wx.Frame):
    def __init__(self, parent, title, style = wx.DEFAULT_FRAME_STYLE, name = wx.FrameNameStr):
        wx.Frame.__init__(self, parent, -1, title, style = style, name = name)

        self.SetIcon(wx.Icon(Icon.get_app_icon_bitmap(IconID.App_Default)))

    def get_scaled_size(self, size: tuple):
        match Platform(Config.Sys.platform):
            case Platform.Windows:
                return self.FromDIP(size)
            
            case Platform.Linux | Platform.macOS:
                return wx.DefaultSize
