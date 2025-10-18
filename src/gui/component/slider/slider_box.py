import wx

from gui.component.panel.panel import Panel
from gui.component.slider.slider import Slider

class SliderBox(Panel):
    def __init__(self, parent: wx.Window, label: str, min_value: int, max_value: int):
        self.label = label
        self.min_value = min_value
        self.max_value = max_value

        Panel.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

    def init_UI(self):
        self.lab = wx.StaticText(self, -1, self.label)
        self.slider = Slider(self, 1, self.min_value, self.max_value)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.lab, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        vbox.Add(self.slider, 0, wx.EXPAND | wx.ALL & (~wx.LEFT) & (~wx.BOTTOM) & (~wx.TOP), self.FromDIP(6))

        self.SetSizer(vbox)

    def Bind_EVT(self):
        self.slider.Bind(wx.EVT_SLIDER, self.onSliderEVT)

    def SetValue(self, value: int):
        self.slider.SetValue(value)

        self.onSliderEVT(0)

    def GetValue(self):
        return self.slider.GetValue()

    def onSliderEVT(self, event: wx.CommandEvent):
        self.lab.SetLabel(f"{self.label}：{self.slider.GetValue()}")
