import wx
import gettext

from gui.component.panel.panel import Panel

from gui.component.spinctrl.label_spinctrl import LabelSpinCtrl

_ = gettext.gettext

class BorderStaticBox(Panel):
    def __init__(self, parent):
        Panel.__init__(self, parent)

        self.init_UI()

    def init_UI(self):
        border_box = wx.StaticBox(self, -1, _("边框"))

        self.border_box = LabelSpinCtrl(border_box, _("边框"), 2.0, "px", wx.HORIZONTAL, float = True)
        self.border_box.SetToolTip(_("边框宽度"))
        self.shadow_box = LabelSpinCtrl(border_box, _("阴影"), 2.0, "px", wx.HORIZONTAL, float = True)
        self.shadow_box.SetToolTip(_("阴影距离"))
        self.non_alpha_chk = wx.CheckBox(border_box, -1, _("不透明背景"))
        self.non_alpha_chk.SetToolTip(_("文字背景不透明"))

        vbox = wx.BoxSizer(wx.HORIZONTAL)
        vbox.Add(self.border_box, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM) | wx.ALIGN_CENTER, self.FromDIP(6))
        vbox.AddSpacer(self.FromDIP(10))
        vbox.Add(self.shadow_box, 0, wx.ALL & (~wx.LEFT) & (~wx.TOP) & (~wx.BOTTOM) | wx.ALIGN_CENTER, self.FromDIP(6))

        border_sbox = wx.StaticBoxSizer(border_box, wx.VERTICAL)
        border_sbox.Add(vbox, 0, wx.EXPAND)
        border_sbox.Add(self.non_alpha_chk, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))

        self.SetSizer(border_sbox)

    def init_data(self, data: dict):
        self.border_box.SetValue(data.get("border"))
        self.shadow_box.SetValue(data.get("shadow"))
        self.non_alpha_chk.SetValue(data.get("non_alpha", False))

    def get_option(self):
        return {
            "border": self.border_box.GetValue(),
            "shadow": self.shadow_box.GetValue(),
            "non_alpha": self.non_alpha_chk.GetValue()
        }