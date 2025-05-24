import wx

from utils.config import Config

from gui.component.dialog import Dialog
from gui.component.text_ctrl import TextCtrl

class CustomUADialog(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent, "自定义 UA")

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

        self.CenterOnParent()

    def init_UI(self):
        ua_lab = wx.StaticText(self, -1, "UA 选项")

        self.custom_ua_radio_btn = wx.RadioButton(self, -1, "自定义")
        self.custom_ua_box = TextCtrl(self, -1, size = self.FromDIP((300, 64)), style = wx.TE_MULTILINE | wx.TE_WORDWRAP)

        self.random_ua_radio_btn = wx.RadioButton(self, -1, "使用随机 UA")

        self.ok_btn = wx.Button(self, wx.ID_OK, "确定", size = self.get_scaled_size((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, "取消", size = self.get_scaled_size((80, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer(1)
        bottom_hbox.Add(self.ok_btn, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        bottom_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(ua_lab, 0, wx.ALL, self.FromDIP(6))
        vbox.Add(self.custom_ua_radio_btn, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        vbox.Add(self.custom_ua_box, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        vbox.Add(self.random_ua_radio_btn, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def Bind_EVT(self):
        self.custom_ua_radio_btn.Bind(wx.EVT_RADIOBUTTON, self.onChangeCustomUAEVT)
        self.random_ua_radio_btn.Bind(wx.EVT_RADIOBUTTON, self.onChangeCustomUAEVT)
    
    def init_utils(self):
        self.custom_ua_box.SetValue(Config.Advanced.custom_ua)

        self.onChangeCustomUAEVT(0)

    def onChangeCustomUAEVT(self, event):
        enable = self.custom_ua_radio_btn.GetValue()

        self.custom_ua_box.Enable(enable)