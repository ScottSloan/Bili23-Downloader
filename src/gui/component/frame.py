import wx

from utils.common.icon_v2 import IconManager, IconType
from utils.config import Config

class Frame(wx.Frame):
    def __init__(self, parent, title, style = wx.DEFAULT_FRAME_STYLE):
        wx.Frame.__init__(self, parent, -1, title, style = style)

        icon_manager = IconManager(self)

        self.SetIcon(wx.Icon(icon_manager.get_icon_bitmap(IconType.APP_ICON_SMALL)))

    def get_scaled_size(self, size: tuple):
        match Config.Sys.platform:
            case "windows":
                return self.FromDIP(size)
            
            case "linux" | "darwin":
                return wx.DefaultSize
