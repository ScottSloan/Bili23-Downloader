import wx

from gui.component.panel.panel import Panel

class StaticBitmap(Panel):
    def __init__(self, parent: wx.Window, size: wx.Size):
        Panel.__init__(self, parent, size = size)

        self.set_dark_mode()

    def onPaintEVT(self, event: wx.PaintEvent):
        dc = wx.BufferedPaintDC(self)

        dc.Clear()

        width, height = self.GetClientSize()

        bmp = self.image.Copy().Scale(width, height, wx.IMAGE_QUALITY_BICUBIC).ConvertToBitmap()

        dc.DrawBitmap(bmp, (0, 0), True)

    def SetBitmap(self, bmp: wx.Bitmap = None, image: wx.Image = None):
        self.image = bmp.ConvertToImage() if bmp else image
        
        self.Bind(wx.EVT_PAINT, self.onPaintEVT)

        self.Refresh()