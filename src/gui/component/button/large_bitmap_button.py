import wx

from utils.config import Config

from utils.common.style.color import Color

from gui.component.panel.panel import Panel

class LargeBitmapButton(Panel):
    def __init__(self, parent, bitmap: wx.Bitmap, label: str):
        Panel.__init__(self, parent)

        self.init_UI(bitmap, label)

        self.Bind_EVT()

        self.lab_hover = False
        
    def init_UI(self, bitmap: wx.Bitmap, label: str):
        self.bitmap = wx.StaticBitmap(self, -1, bitmap)
        self.label = wx.StaticText(self, -1, label)

        bitmap_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bitmap_hbox.AddStretchSpacer()
        bitmap_hbox.Add(self.bitmap, 0, wx.ALL, self.FromDIP(6))
        bitmap_hbox.AddStretchSpacer()

        label_hbox = wx.BoxSizer(wx.HORIZONTAL)
        label_hbox.AddStretchSpacer()
        label_hbox.Add(self.label, 0, wx.ALL, self.FromDIP(6))
        label_hbox.AddStretchSpacer()

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(bitmap_hbox, 0, wx.EXPAND)
        vbox.Add(label_hbox, 0, wx.EXPAND)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.AddSpacer(self.FromDIP(10))
        hbox.Add(vbox, 0, wx.EXPAND)
        hbox.AddSpacer(self.FromDIP(10))

        self.SetSizer(hbox)

    def Bind_EVT(self):
        self.Bind(wx.EVT_ENTER_WINDOW, self.onHoverEVT)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.onLeaveEVT)
        self.Bind(wx.EVT_LEFT_DOWN, self.onClickEVT)

        self.bitmap.Bind(wx.EVT_ENTER_WINDOW, self.onLabHoverEVT)
        self.bitmap.Bind(wx.EVT_LEAVE_WINDOW, self.onLabLeaveEVT)
        self.bitmap.Bind(wx.EVT_LEFT_DOWN, self.onClickEVT)

        self.label.Bind(wx.EVT_ENTER_WINDOW, self.onLabHoverEVT)
        self.label.Bind(wx.EVT_LEAVE_WINDOW, self.onLabLeaveEVT)
        self.label.Bind(wx.EVT_LEFT_DOWN, self.onClickEVT)

    def onHoverEVT(self, event):
        self.set_hover_bgcolor()

        self.Refresh()

        event.Skip()

    def onLeaveEVT(self, event):
        if not self.lab_hover:
            self.set_default_bgcolor()

        self.Refresh()

        event.Skip()

    def onLabHoverEVT(self, event):
        self.lab_hover = True

        event.Skip()

    def onLabLeaveEVT(self, event):
        self.lab_hover = False

        event.Skip()

    def onClickEVT(self, event):
        self.onClickCustomEVT()

    def set_hover_bgcolor(self):
        if Config.Sys.dark_mode:
            self.SetBackgroundColour(wx.Colour(60, 60, 60))
        else:
            self.SetBackgroundColour(wx.Colour(200, 200, 200))

    def set_default_bgcolor(self):
        self.SetBackgroundColour(Color.get_panel_background_color())

    def onClickCustomEVT(self):
        pass