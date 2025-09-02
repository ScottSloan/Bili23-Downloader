import wx

from utils.config import Config
from utils.common.style.color import Color

from gui.component.panel.panel import Panel
from gui.component.staticbitmap.staticbitmap import StaticBitmap

class ActionButton(Panel):
    def __init__(self, parent: wx.Window, title: str, name: str = wx.PanelNameStr):
        self._title = title

        Panel.__init__(self, parent, name = name)

        self.init_UI()

        self.Bind_EVT()

        self.active_flag = False
        self.lab_hover_flag = False

        self.set_unactive_bgcolor()

    def init_UI(self):
        self.icon = StaticBitmap(self, size = self.FromDIP((16, 16)))

        self.lab = wx.StaticText(self, -1, self._title)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.AddSpacer(self.FromDIP(33))
        hbox.Add(self.icon, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        hbox.Add(self.lab, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        hbox.AddSpacer(self.FromDIP(33))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.AddSpacer(self.FromDIP(3))
        vbox.Add(hbox, 0, wx.EXPAND)
        vbox.AddSpacer(self.FromDIP(3))

        self.SetSizerAndFit(vbox)
    
    def Bind_EVT(self):
        self.Bind(wx.EVT_ENTER_WINDOW, self.onHoverEVT)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.onLeaveEVT)
        self.Bind(wx.EVT_LEFT_DOWN, self.onClickEVT)

        self.lab.Bind(wx.EVT_ENTER_WINDOW, self.onLabHoverEVT)
        self.lab.Bind(wx.EVT_LEAVE_WINDOW, self.onLabLeaveEVT)
        self.lab.Bind(wx.EVT_LEFT_DOWN, self.onClickEVT)

        self.icon.Bind(wx.EVT_ENTER_WINDOW, self.onLabHoverEVT)
        self.icon.Bind(wx.EVT_LEAVE_WINDOW, self.onLabLeaveEVT)
        self.icon.Bind(wx.EVT_LEFT_DOWN, self.onClickEVT)

    def onHoverEVT(self, event):
        if not self.active_flag:
            self.set_hover_bgcolor()

            self.Refresh()

        event.Skip()

    def onLabHoverEVT(self, event):
        self.lab_hover_flag = True

        event.Skip()
    
    def onLeaveEVT(self, event):
        if not self.active_flag and not self.lab_hover_flag:
            self.set_unactive_bgcolor()

            self.Refresh()

        event.Skip()

    def onLabLeaveEVT(self, event):
        self.lab_hover_flag = False

        event.Skip()
    
    def onClickEVT(self, event):
        self.set_active_bgcolor()

        self.active_flag = True

        self.onClickCustomEVT()

        if event:
            event.Skip()
    
    def setActiveState(self):
        self.active_flag = True

        self.set_active_bgcolor()

    def setUnactiveState(self):
        self.active_flag = False

        self.set_unactive_bgcolor()

    def set_active_bgcolor(self):
        if Config.Sys.dark_mode:
            self.SetBackgroundColour(wx.Colour(21, 21, 21))
        else:
            self.SetBackgroundColour(wx.Colour(210, 210, 210))

        self.Refresh()

    def set_unactive_bgcolor(self):
        if Config.Sys.dark_mode:
            self.SetBackgroundColour(Color.get_panel_background_color())
        else:
            self.SetBackgroundColour("white")

        self.Refresh()

    def set_hover_bgcolor(self):
        if Config.Sys.dark_mode:
            self.SetBackgroundColour(wx.Colour(60, 60, 60))
        else:
            self.SetBackgroundColour(wx.Colour(220, 220, 220))

        self.Refresh()

    def setBitmap(self, bitmap):
        self.icon.SetBitmap(bmp = bitmap)

    def setTitle(self, title):
        self.lab.SetLabel(title)

    def onClickCustomEVT(self):
        pass
