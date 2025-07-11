import wx

from gui.component.panel.panel import Panel

class LabelSpinCtrl(Panel):
    def __init__(self, parent, label: str, value: int):
        self.label = label
        self.value = value

        Panel.__init__(self, parent)

        self.init_UI()

    def init_UI(self):
        label = wx.StaticText(self, -1, self.label)

        lab_hbox = wx.BoxSizer(wx.HORIZONTAL)
        lab_hbox.AddStretchSpacer()
        lab_hbox.Add(label, 0, wx.ALL & (~wx.BOTTOM), self.FromDIP(6))
        lab_hbox.AddStretchSpacer()

        self.spinctrl = wx.SpinCtrl(self, -1, min = 0, max = 100, initial = self.value)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(lab_hbox, 0, wx.EXPAND)
        vbox.Add(self.spinctrl, 0, wx.ALL, self.FromDIP(6))

        self.SetSizer(vbox)