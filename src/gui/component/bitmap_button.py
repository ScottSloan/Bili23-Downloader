import wx

from utils.config import Config
from utils.common.enums import Platform

class BitmapButton(wx.BitmapButton):
    def __init__(self, parent, bitmap):
        def get_bitmap_button_style():
            match Platform(Config.Sys.platform):
                case Platform.Windows:
                    return 0
                
                case Platform.Linux | Platform.macOS:
                    return wx.NO_BORDER

        wx.BitmapButton.__init__(self, parent, -1, bitmap = bitmap, size = parent.FromDIP((24, 24)), style = get_bitmap_button_style())