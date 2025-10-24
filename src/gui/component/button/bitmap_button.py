import wx
from wx.lib.buttons import ThemedGenBitmapButton

from utils.config import Config
from utils.common.enums import Platform

if Platform(Config.Sys.platform) == Platform.Windows:
    impl = ThemedGenBitmapButton
else:
    impl = wx.BitmapButton

class BitmapButton(impl):
    def __init__(self, parent: wx.Window, bitmap: wx.Bitmap, size = None, enable: bool = True, tooltip: str = ""):
        if not size:
            size = self.GetSizeEx(parent)

        impl.__init__(self, parent, -1, bitmap = bitmap, size = size, style = self.get_style())

        self.Enable(enable)
        self.SetToolTip(tooltip)

    def Bind(self, event, handler, source = None, id = wx.ID_ANY, id2 = wx.ID_ANY):
        return super().Bind(event, handler, source, id, id2)

    def get_style(self):
        match Platform(Config.Sys.platform):
            case Platform.Windows:
                return 0

            case Platform.Linux | Platform.macOS:
                return wx.BORDER_NONE
            
    def SetBitmap(self, bitmap: wx.Bitmap, dir = wx.LEFT):
        match Platform(Config.Sys.platform):
            case Platform.Windows:
                self.SetBitmapLabel(bitmap)

            case Platform.Linux | Platform.macOS:
                return super().SetBitmap(bitmap, dir)
            
    def SetToolTip(self, tip: str):
        return super().SetToolTip(tip)
    
    def GetSizeEx(self, parent: wx.Window):
        match Platform(Config.Sys.platform):
            case Platform.Windows | Platform.macOS:
                return parent.FromDIP((24, 24))

            case Platform.Linux:
                return parent.FromDIP((24, 24))