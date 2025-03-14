import wx

from wx.lib.scrolledpanel import ScrolledPanel as _ScrolledPanel

class ScrolledPanel(_ScrolledPanel):
    def __init__(self, parent, size = wx.DefaultSize):
        _ScrolledPanel.__init__(self, parent, -1, size = size)

        self.sizer = wx.BoxSizer(wx.VERTICAL)

        self.SetSizer(self.sizer)
