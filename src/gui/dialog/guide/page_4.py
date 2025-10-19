import wx
import wx.adv
import gettext

from utils.config import Config
from utils.common.data.guide import guide_4_msg

from gui.component.panel.panel import Panel

_ = gettext.gettext

class Page4Panel(Panel):
    def __init__(self, parent: wx.Window):
        Panel.__init__(self, parent)

        self.init_UI()

    def init_UI(self):
        font = self.GetFont()
        font.SetFractionalPointSize(font.GetFractionalPointSize() + 1)

        self.desc_lab = wx.StaticText(self, -1, guide_4_msg)
        self.desc_lab.Wrap(self.FromDIP(400))
        self.desc_lab.SetFont(font)

        self.enable_listen_clipboard_chk = wx.CheckBox(self, -1, _("自动监听剪切板，检测到复制视频链接时自动解析"))
        self.enable_listen_clipboard_chk.SetFont(font)
        self.enable_switch_cdn_chk = wx.CheckBox(self, -1, _("自动切换音视频流 CDN (国内用户建议开启)"))
        self.enable_switch_cdn_chk.SetValue(Config.Basic.language == "zh_CN")
        self.enable_switch_cdn_chk.SetFont(font)

        relative_url = wx.StaticText(self, -1, _("相关链接"))
        relative_url.SetFont(font)
        document_link = wx.adv.HyperlinkCtrl(self, -1, _("说明文档"), url = "https://bili23.scott-sloan.cn/doc/use/basic.html")
        document_link.SetFont(font)

        link_hbox = wx.BoxSizer(wx.HORIZONTAL)
        link_hbox.Add(relative_url, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(10))
        link_hbox.Add(document_link, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(10))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.desc_lab, 0, wx.ALL & (~wx.BOTTOM), self.FromDIP(10))
        vbox.AddStretchSpacer()
        vbox.Add(self.enable_listen_clipboard_chk, 0, wx.ALL & (~wx.BOTTOM) & (~wx.TOP), self.FromDIP(10))
        vbox.AddSpacer(self.FromDIP(6))
        vbox.Add(self.enable_switch_cdn_chk, 0, wx.ALL & (~wx.TOP), self.FromDIP(10))
        vbox.AddStretchSpacer()
        vbox.Add(link_hbox, 0, wx.EXPAND)

        self.SetSizer(vbox)

    def save(self):
        Config.Basic.is_new_user = False

        Config.Basic.listen_clipboard = self.enable_listen_clipboard_chk.GetValue()
        Config.Advanced.enable_switch_cdn = self.enable_switch_cdn_chk.GetValue()

        Config.save_app_config()

    def onChangePage(self):
        return {
            "title": _("完成"),
            "next_btn_label": _("完成"),
            "next_btn_enable": True
        }