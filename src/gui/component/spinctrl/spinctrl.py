import wx

class SpinCtrl(wx.SpinCtrl):
    def __init__(self, parent: wx.Window, value: str = "", min: int = 0, max: int = 100, size: wx.Size = wx.DefaultSize):
        wx.SpinCtrl.__init__(self, parent, -1, value = value, min = min, max = max, size = size, style = 0)
