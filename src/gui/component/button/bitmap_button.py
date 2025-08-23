import wx
from wx.lib.buttons import ThemedGenBitmapButton

from utils.config import Config
from utils.common.enums import Platform

if Platform(Config.Sys.platform) == Platform.Windows:
    impl = ThemedGenBitmapButton
else:
    impl = wx.BitmapButton

class BitmapButton(impl):
    def __init__(self, parent: wx.Window, bitmap: wx.Bitmap, enable: bool = True, tooltip: str = ""):
        impl.__init__(self, parent, -1, bitmap = bitmap, size = parent.FromDIP((24, 24)), style = self.get_style())

        self.Enable(enable)
        self.SetToolTip(tooltip)

    def get_style(self):
        match Platform(Config.Sys.platform):
            case Platform.Windows:
                return 0

            case Platform.Linux | Platform.macOS:
                return wx.BORDER_NONE