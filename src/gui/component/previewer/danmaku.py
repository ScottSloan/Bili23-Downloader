import wx

from gui.component.panel.panel import Panel

class DanmakuPreviewer(Panel):
    def __init__(self, parent):
        Panel.__init__(self, parent)

        self.Bind(wx.EVT_PAINT, self.onPaintEVT)

    def onPaintEVT(self, event: wx.PaintEvent):
        dc = wx.PaintDC(self)
        self.render_danmaku(dc)

    def render_danmaku(self, dc: wx.PaintDC):
        dc.DrawText("Text", 10, 10)