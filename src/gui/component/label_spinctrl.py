import wx

from gui.component.panel.panel import Panel

class LabelSpinCtrl(Panel):
    def __init__(self, parent, label: str, value: int | float, unit: str, orient: int = wx.HORIZONTAL, float: int = False):
        self.label, self.value, self.unit, self.float = label, value, unit, float

        Panel.__init__(self, parent)

        match orient:
            case wx.VERTICAL:
                self.init_vertical_UI()

            case wx.HORIZONTAL:
                self.init_horizontal_UI()

    def init_vertical_UI(self):
        label = wx.StaticText(self, -1, self.label)

        lab_hbox = wx.BoxSizer(wx.HORIZONTAL)
        lab_hbox.AddStretchSpacer()
        lab_hbox.Add(label, 0, wx.ALL & (~wx.BOTTOM), self.FromDIP(6))
        lab_hbox.AddStretchSpacer()

        self.spinctrl = wx.SpinCtrl(self, -1, min = 0, max = 100, initial = self.value)
        unit_lab = wx.StaticText(self, -1, self.unit)

        spin_hbox = wx.BoxSizer(wx.HORIZONTAL)
        spin_hbox.Add(self.spinctrl, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))
        spin_hbox.Add(unit_lab, 0, wx.ALL & (~wx.LEFT) & (~wx.RIGHT) | wx.ALIGN_CENTER, self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(lab_hbox, 0, wx.EXPAND)
        vbox.Add(spin_hbox, 0, wx.EXPAND)

        self.SetSizer(vbox)

    def init_horizontal_UI(self):
        label = wx.StaticText(self, -1, self.label)
        self.spinctrl = wx.SpinCtrlDouble(self, -1, min = 0.0, max = 100.0, initial = self.value, inc = 0.1)
        unit_lab = wx.StaticText(self, -1, self.unit)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(label, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        hbox.Add(self.spinctrl, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))
        hbox.Add(unit_lab, 0, wx.ALL & (~wx.LEFT) & (~wx.RIGHT) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.SetSizer(hbox)

    def SetValue(self, value: int | float):
        self.spinctrl.SetValue(value)

    def GetValue(self):
        return self.spinctrl.GetValue()
    
    def SetToolTip(self, tip: str):
        self.spinctrl.SetToolTip(tip)