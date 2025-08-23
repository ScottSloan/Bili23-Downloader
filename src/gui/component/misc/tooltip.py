import wx

from utils.common.style.icon_v4 import Icon, IconID

from gui.component.staticbitmap.staticbitmap import StaticBitmap

class ToolTip(StaticBitmap):
    def __init__(self, parent: wx.Window):
        StaticBitmap.__init__(self, parent, size = parent.FromDIP((16, 16)))

        self.SetBitmap(bmp = Icon.get_icon_bitmap(IconID.Info))

    def set_tooltip(self, string: str):
        tooltip = wx.ToolTip(string)
        tooltip.SetDelay(50)
        tooltip.SetAutoPop(30000)

        self.SetToolTip(tooltip)

        self.Refresh()