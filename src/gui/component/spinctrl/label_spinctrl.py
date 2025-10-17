import wx

from utils.config import Config
from utils.common.enums import Platform

from gui.component.panel.panel import Panel
from gui.component.spinctrl.spinctrl import SpinCtrl


class LabelSpinCtrl(Panel):
    def __init__(self, parent, label: str, value: int | float, unit: str, orient: int = wx.HORIZONTAL, float: int = False, max: int = 100, min: int = 0):
        self.label, self.value, self.unit, self.float, self.max, self.min = label, value, unit, float, max, min

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

        self.spinctrl = self.get_spinctrl()
        unit_lab = wx.StaticText(self, -1, self.unit)

        spin_hbox = wx.BoxSizer(wx.HORIZONTAL)
        spin_hbox.Add(self.spinctrl, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        spin_hbox.Add(unit_lab, 0, wx.ALL & (~wx.LEFT) & (~wx.RIGHT) | wx.ALIGN_CENTER, self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(lab_hbox, 0, wx.EXPAND)
        vbox.Add(spin_hbox, 0, wx.EXPAND)

        self.SetSizer(vbox)

    def init_horizontal_UI(self):
        label = wx.StaticText(self, -1, self.label)
        self.spinctrl = self.get_spinctrl()
        unit_lab = wx.StaticText(self, -1, self.unit)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(label, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        hbox.Add(self.spinctrl, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        hbox.Add(unit_lab, 0, wx.ALL & (~wx.LEFT) & (~wx.RIGHT) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.SetSizer(hbox)

    def SetValue(self, value: int | float):
        self.spinctrl.SetValue(value)

    def GetValue(self):
        return self.spinctrl.GetValue()
    
    def SetToolTip(self, tip: str):
        self.spinctrl.SetToolTip(tip)

    def get_spinctrl(self):
        if self.float:
            spinctrl = wx.SpinCtrlDouble(self, -1, value = str(self.value), size = self.get_size(), min = self.min, max = self.max, inc = 0.1)
            spinctrl.SetDigits(1)
        
        else:
            spinctrl = SpinCtrl(self, value = str(self.value), min = self.min, max = self.max, size = self.get_size())

        return spinctrl

    def get_size(self):
        match Platform(Config.Sys.platform):
            case Platform.Windows | Platform.macOS:
                return self.FromDIP((55, -1))
            
            case Platform.Linux:
                return self.FromDIP((130, -1))