import wx

from gui.component.panel.panel import Panel

class LabelSlider(Panel):
    def __init__(self, parent: wx.Window, data: dict):
        Panel.__init__(self, parent)

        self.label: str = data.get("label")
        self.value: int = data.get("value")
        self.min_value: int = data.get("min_value")
        self.max_value: int = data.get("max_value")
        self.data: dict[int, str] = data.get("data")

        self.init_UI()

        self.Bind_EVT()

    def init_UI(self):
        self.label = wx.StaticText(self, -1, self.label)
        self.slider = wx.Slider(self, -1, value = self.value, minValue = self.min_value, maxValue=self.max_value)
        self.indicator_lab = wx.StaticText(self, -1, self.get_indicator(self.value))

        self.slider.Bind(wx.EVT_SLIDER, self.onSliderEVT)

        sizer = wx.BoxSizer(wx.HORIZONTAL)
        sizer.Add(self.label, 0, wx.ALL & (~wx.BOTTOM) | wx.ALIGN_CENTER, self.FromDIP(5))
        sizer.Add(self.slider, 1, wx.ALL & (~wx.LEFT) & (~wx.BOTTOM) | wx.ALIGN_CENTER, self.FromDIP(6))
        sizer.Add(self.indicator_lab, 0, wx.ALL & (~wx.LEFT) & (~wx.BOTTOM) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.SetSizer(sizer)

    def Bind_EVT(self):
        self.slider.Bind(wx.EVT_SLIDER, self.onSliderEVT)

    def onSliderEVT(self, event: wx.CommandEvent):
        value = self.slider.GetValue()

        self.indicator_lab.SetLabel(self.get_indicator(value))

    def get_indicator(self, value: int):
        return self.data.get(value, f"{value}%")
    
    def SetValue(self, value: int):
        self.slider.SetValue(value)
        
        self.onSliderEVT(0)

    def GetValue(self):
        return self.slider.GetValue()