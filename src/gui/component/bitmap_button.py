import wx

from utils.config import Config

class BitmapButton(wx.BitmapButton):
    def __init__(self, parent, bitmap):
        def get_bitmap_button_style():
            match Config.Sys.platform:
                case "windows" | "darwin":
                    return 0
                
                case "linux":
                    return wx.NO_BORDER

        wx.BitmapButton.__init__(self, parent, -1, bitmap = bitmap, size = parent.FromDIP((24, 24)), style = get_bitmap_button_style())