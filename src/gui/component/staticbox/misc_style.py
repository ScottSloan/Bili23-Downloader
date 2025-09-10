import wx

from gui.component.panel.panel import Panel
from gui.component.spinctrl.label_spinctrl import LabelSpinCtrl

class MiscStyleStaticBox(Panel):
    def __init__(self, parent: wx.Window):
        Panel.__init__(self, parent)

        self.init_UI()

    def init_UI(self):
        misc_box = wx.StaticBox(self, -1, "杂项")

        self.scale_x_box = LabelSpinCtrl(misc_box, "水平缩放", 100, "%", wx.HORIZONTAL, float = False, max = 1000)
        self.scale_x_box.SetToolTip("水平缩放百分比")
        self.scale_y_box = LabelSpinCtrl(misc_box, "垂直缩放", 100, "%", wx.HORIZONTAL, float = False, max = 1000)
        self.scale_y_box.SetToolTip("垂直缩放百分比")

        self.angle_box = LabelSpinCtrl(misc_box, "旋转角度", 0, "°", wx.HORIZONTAL, float = False, max = 360, min = -360)
        self.angle_box.SetToolTip("旋转角度")
        self.spacing_box = LabelSpinCtrl(misc_box, "字符间距", 0, "px", wx.HORIZONTAL, float = True, max = 100)
        self.spacing_box.SetToolTip("字符间距")

        flex_sizer = wx.FlexGridSizer(2, 3, 0, 0)
        flex_sizer.Add(self.scale_x_box, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM), self.FromDIP(6))
        flex_sizer.AddSpacer(self.FromDIP(10))
        flex_sizer.Add(self.scale_y_box, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM), self.FromDIP(6))
        flex_sizer.Add(self.angle_box, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM), self.FromDIP(6))
        flex_sizer.AddSpacer(self.FromDIP(10))
        flex_sizer.Add(self.spacing_box, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM), self.FromDIP(6))
        
        misc_sbox = wx.StaticBoxSizer(misc_box, wx.VERTICAL)
        misc_sbox.Add(flex_sizer, 0, wx.EXPAND)

        self.SetSizer(misc_sbox)

    def init_data(self, data: dict):
        self.scale_x_box.SetValue(data.get("scale_x"))
        self.scale_y_box.SetValue(data.get("scale_y"))
        self.angle_box.SetValue(data.get("angle"))
        self.spacing_box.SetValue(data.get("spacing"))

    def get_option(self):
        return {
            "scale_x": self.scale_x_box.GetValue(),
            "scale_y": self.scale_y_box.GetValue(),
            "angle": self.angle_box.GetValue(),
            "spacing": self.spacing_box.GetValue()
        }