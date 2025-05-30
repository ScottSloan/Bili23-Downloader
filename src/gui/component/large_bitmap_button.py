import wx

from gui.component.panel import Panel

class LargeBitmapButton(Panel):
    def __init__(self, parent, bitmap: wx.Bitmap, label: str):
        Panel.__init__(self, parent)

        self.init_UI(bitmap, label)

    def init_UI(self, bitmap: wx.Bitmap, label: str):
        self.bitmap = wx.StaticBitmap(self, -1, bitmap)
        self.label = wx.StaticText(self, -1, label)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.bitmap, 0, wx.ALL, self.FromDIP(6))
        vbox.Add(self.label, 0, wx.ALL, self.FromDIP(6))

        self.SetSizerAndFit(vbox)