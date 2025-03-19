import wx
import wx.core

from utils.config import Config

from gui.component.panel import Panel

class ActionButton(Panel):
    def __init__(self, parent, title):
        self._title = title

        Panel.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

        self._active = False
        self._lab_hover = False

    def init_UI(self):
        self.icon = wx.StaticBitmap(self, -1, size = self.FromDIP((20, 20)))

        self.lab = wx.StaticText(self, -1, self._title)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.AddSpacer(self.FromDIP(33))
        hbox.Add(self.icon, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        hbox.Add(self.lab, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, 10)
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

    def onHoverEVT(self, event):
        if not self._active:
            self.set_hover_bgcolor()

            self.Refresh()

        event.Skip()

    def onLabHoverEVT(self, event):
        self._lab_hover = True

        event.Skip()
    
    def onLeaveEVT(self, event):
        if not self._active and not self._lab_hover:
            self.set_unactive_bgcolor()

            self.Refresh()

        event.Skip()

    def onLabLeaveEVT(self, event):
        self._lab_hover = False

        event.Skip()
    
    def onClickEVT(self, event):
        self.set_active_bgcolor()

        self.Refresh()

        self._active = True

        self.onClickCustomEVT()

        event.Skip()
    
    def setActiveState(self):
        self._active = True
        self.set_active_bgcolor()

        self.Refresh()

    def setUnactiveState(self):
        self._active = False
        self.set_unactive_bgcolor()

        self.Refresh()

    def set_active_bgcolor(self):
        if Config.Sys.dark_mode:
            self.SetBackgroundColour(wx.Colour(21, 21, 21))
        else:
            self.SetBackgroundColour(wx.Colour(210, 210, 210))

    def set_unactive_bgcolor(self):
        if Config.Sys.dark_mode:
            self.SetBackgroundColour(wx.SystemSettings.GetColour(getattr(wx, "SYS_COLOUR_FRAMEBK")))
        else:
            self.SetBackgroundColour("white")

    def set_hover_bgcolor(self):
        if Config.Sys.dark_mode:
            self.SetBackgroundColour(wx.Colour(60, 60, 60))
        else:
            self.SetBackgroundColour(wx.Colour(220, 220, 220))

    def setBitmap(self, bitmap):
        self.icon.SetBitmap(bitmap)

    def setTitle(self, title):
        self.lab.SetLabel(title)

    def onClickCustomEVT(self):
        pass
