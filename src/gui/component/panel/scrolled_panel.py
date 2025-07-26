import wx

from wx.lib.scrolledpanel import ScrolledPanel as _ScrolledPanel

from utils.config import Config

class ScrolledPanel(_ScrolledPanel):
    def __init__(self, parent, size = wx.DefaultSize):
        _ScrolledPanel.__init__(self, parent, -1, size = size)

        self.sizer = wx.BoxSizer(wx.VERTICAL)

        self.SetSizer(self.sizer)

    def set_dark_mode(self):
        if not Config.Sys.dark_mode:
            self.SetBackgroundColour("white")

    def Layout(self, scroll_x = False, scrollToTop = False):
        super().Layout()

        self.SetupScrolling(scroll_x = scroll_x, scrollToTop = scrollToTop)
        
