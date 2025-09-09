import wx

from gui.component.panel.panel import Panel

from gui.component.misc.label_spinctrl import LabelSpinCtrl

class BorderStaticBox(Panel):
    def __init__(self, parent):
        Panel.__init__(self, parent)

        self.init_UI()

    def init_UI(self):
        border_box = wx.StaticBox(self, -1, "边框")

        self.border_box = LabelSpinCtrl(border_box, "边框", 2.0, "px", wx.HORIZONTAL, float = True)
        self.border_box.SetToolTip("边框宽度")
        self.shadow_box = LabelSpinCtrl(border_box, "阴影", 2.0, "px", wx.HORIZONTAL, float = True)
        self.shadow_box.SetToolTip("阴影距离")
        self.non_alpha_chk = wx.CheckBox(border_box, -1, "不透明背景")
        self.non_alpha_chk.SetToolTip("文字背景不透明")

        border_sbox = wx.StaticBoxSizer(border_box, wx.HORIZONTAL)
        border_sbox.Add(self.border_box, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM) | wx.ALIGN_CENTER, self.FromDIP(6))
        border_sbox.AddSpacer(self.FromDIP(10))
        border_sbox.Add(self.shadow_box, 0, wx.ALL & (~wx.LEFT) & (~wx.TOP) & (~wx.BOTTOM) | wx.ALIGN_CENTER, self.FromDIP(6))
        border_sbox.Add(self.non_alpha_chk, 0, wx.ALL & (~wx.LEFT) & (~wx.TOP) & (~wx.BOTTOM) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.SetSizer(border_sbox)

    def init_data(self, data: dict):
        self.border_box.SetValue(data.get("border"))
        self.shadow_box.SetValue(data.get("shadow"))

    def get_option(self):
        return {
            "border": self.border_box.GetValue(),
            "shadow": self.shadow_box.GetValue()
        }