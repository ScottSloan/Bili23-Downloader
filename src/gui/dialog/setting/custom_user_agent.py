import wx

from utils.config import Config

from gui.component.window.dialog import Dialog

class CustomUADialog(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent, "自定义 User-Agent")

        self.init_UI()

        self.init_utils()

        self.CenterOnParent()

    def init_UI(self):
        ua_lab = wx.StaticText(self, -1, "User-Agent")

        self.custom_ua_box = wx.TextCtrl(self, -1, size = self.FromDIP((400, 64)), style = wx.TE_MULTILINE | wx.TE_WORDWRAP)

        self.ok_btn = wx.Button(self, wx.ID_OK, "确定", size = self.get_scaled_size((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, "取消", size = self.get_scaled_size((80, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer(1)
        bottom_hbox.Add(self.ok_btn, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        bottom_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(ua_lab, 0, wx.ALL, self.FromDIP(6))
        vbox.Add(self.custom_ua_box, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)
    
    def init_utils(self):
        self.custom_ua_box.SetValue(Config.Advanced.user_agent)

    def onOKEVT(self):
        if not self.custom_ua_box.GetValue():
            wx.MessageDialog(self, "User-Agent 无效\n\nUser-Agent 不能为空", "警告", wx.ICON_WARNING).ShowModal()
            return

        Config.Temp.user_agent = self.custom_ua_box.GetValue()