import wx

from gui.component.panel.panel import Panel

class SpinCtrl(Panel):
    def __init__(self, parent: wx.Window, value: int = 0, max: int = 100, min: int = 0, increment: int = 1):
        self.value = value
        self.max = max
        self.min = min
        self.increment = increment

        Panel.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

    def init_UI(self):
        self.box = wx.TextCtrl(self, -1, "100", size = self.FromDIP((45, -1)))

        h = self.box.GetSize().height

        self.spin_btn = wx.SpinButton(self, -1, size = self.FromDIP((-1, self.ToDIP(h))))
        self.spin_btn.SetRange(self.min, self.max)
        self.spin_btn.SetValue(self.value)
        self.spin_btn.SetIncrement(self.increment)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.box)
        hbox.AddSpacer(self.FromDIP(1))
        hbox.Add(self.spin_btn)

        self.SetSizer(hbox)

    def Bind_EVT(self):
        self.spin_btn.Bind(wx.EVT_SPIN, self.onSpinEVT)
        self.box.Bind(wx.EVT_TEXT, self.onTextEVT)

    def onSpinEVT(self, event: wx.SpinEvent):
        self.box.SetLabel(str(self.spin_btn.GetValue()))

        self.box.SetFocus()
        self.box.SetInsertionPointEnd()
        self.box.SelectAll()

    def onTextEVT(self, event: wx.CommandEvent):
        self.spin_btn.SetValue(int(self.box.GetValue()))

    def SetValue(self, value: int):
        self.spin_btn.SetValue(value)
        self.box.SetLabel(str(value))

    def GetValue(self):
        return self.spin_btn.GetValue()
