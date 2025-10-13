import wx
import os
import wx.adv
import gettext

from utils.config import Config

from utils.common.style.icon_v4 import Icon, IconID, IconSize
from utils.common.style.color import Color
from utils.common.compile_data import date

from gui.component.window.dialog import Dialog
from gui.component.panel.panel import Panel
from gui.component.staticbitmap.staticbitmap import StaticBitmap
from gui.component.label.info_label import InfoLabel

_ = gettext.gettext

class URLBox(Panel):
    def __init__(self, parent: wx.Window, label: str, url: str):
        self.label = label
        self.url = url

        Panel.__init__(self, parent)

        self.init_UI()

    def init_UI(self):
        lab = wx.StaticText(self, -1, self.label)
        link = wx.adv.HyperlinkCtrl(self, url = self.url)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(lab, 0, wx.ALIGN_CENTER)
        hbox.Add(link, 0, wx.ALIGN_CENTER)

        self.SetSizer(hbox)

class AboutWindow(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent, _("关于 %s") % Config.APP.name, style = wx.DEFAULT_DIALOG_STYLE & (~wx.CAPTION) | wx.RESIZE_BORDER)

        self.init_UI()

        self.CenterOnParent()

        wx.Bell()
    
    def init_UI(self):
        self.set_dark_mode()

        logo = StaticBitmap(self, bmp = Icon.get_icon_bitmap(IconID.App_Default, IconSize.LARGE), size = self.FromDIP((64, 64)))

        logo_vbox = wx.BoxSizer(wx.VERTICAL)
        logo_vbox.Add(logo, 0, wx.ALL, self.FromDIP(6))

        title_font: wx.Font = self.GetFont()
        title_font.SetFractionalPointSize(int(title_font.GetFractionalPointSize() + 4))

        version_font: wx.Font = self.GetFont()
        version_font.SetFractionalPointSize(int(version_font.GetFractionalPointSize() + 2))

        title_lab = wx.StaticText(self, -1, Config.APP.name)
        title_lab.SetForegroundColour(Color.get_frame_text_color())
        title_lab.SetFont(title_font.MakeBold())

        desc_lab = wx.StaticText(self, -1, _("跨平台的B站视频下载工具"))
        desc_lab.SetForegroundColour(Color.get_frame_text_color())

        version_lab = wx.StaticText(self, -1, _("版本 %s") % self.GetVersion())
        version_lab.SetFont(version_font)
        version_lab.SetForegroundColour(Color.get_frame_text_color())

        license_lab = wx.StaticText(self, -1, _("本程序为免费开源软件，遵循 MIT 许可证发布"))
        license_lab.SetForegroundColour(Color.get_frame_text_color())

        copyright_lab = wx.StaticText(self, -1, "Copyright © 2022-2025 Scott Sloan. All rights reserved.")
        copyright_lab.SetForegroundColour(Color.get_frame_text_color())

        homepage_link = wx.adv.HyperlinkCtrl(self, -1, _("官方网站"), url = "https://bili23.scott-sloan.cn")
        github_link = wx.adv.HyperlinkCtrl(self, -1, _("项目首页"), url = "https://www.github.com/ScottSloan/Bili23-Downloader")

        opensource_link = wx.adv.HyperlinkCtrl(self, -1, _("开源许可"), url = "https://bili23.scott-sloan.cn/doc/license.html")
        disclaimer_link = wx.adv.HyperlinkCtrl(self, -1, _("免责声明"), url = "https://bili23.scott-sloan.cn/doc/announcement.html")

        link_hbox = wx.BoxSizer(wx.HORIZONTAL)
        link_hbox.Add(homepage_link, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        link_hbox.Add(wx.StaticText(self, -1, "•"), 0, wx.ALL & (~wx.LEFT) & (~wx.RIGHT) | wx.ALIGN_CENTER, self.FromDIP(6))
        link_hbox.Add(github_link, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        link_hbox.Add(wx.StaticText(self, -1, "•"), 0, wx.ALL & (~wx.LEFT) & (~wx.RIGHT) | wx.ALIGN_CENTER, self.FromDIP(6))
        link_hbox.Add(opensource_link, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        link_hbox.Add(wx.StaticText(self, -1, "•"), 0, wx.ALL & (~wx.LEFT) & (~wx.RIGHT) | wx.ALIGN_CENTER, self.FromDIP(6))
        link_hbox.Add(disclaimer_link, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))

        ok_btn = wx.Button(self, wx.ID_OK, _("确定"), size = self.get_scaled_size((80, 30)))

        btn_hbox = wx.BoxSizer(wx.HORIZONTAL)
        btn_hbox.AddStretchSpacer()
        btn_hbox.Add(ok_btn)

        body_vbox = wx.BoxSizer(wx.VERTICAL)
        body_vbox.Add(title_lab, 0, wx.ALL, self.FromDIP(6))
        body_vbox.Add(desc_lab, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        body_vbox.AddSpacer(self.FromDIP(6))
        body_vbox.Add(version_lab, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        body_vbox.Add(license_lab, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM), self.FromDIP(6))
        body_vbox.Add(copyright_lab, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM), self.FromDIP(6))
        body_vbox.Add(link_hbox, 0, wx.EXPAND)
        body_vbox.AddSpacer(self.FromDIP(6))
        body_vbox.Add(btn_hbox, 0, wx.EXPAND)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(logo_vbox, 0, wx.EXPAND, self.FromDIP(6))
        hbox.AddSpacer(self.FromDIP(6))
        hbox.Add(body_vbox, 0, wx.EXPAND, self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(hbox, 0, wx.ALL | wx.EXPAND, self.FromDIP(20))

        self.SetSizerAndFit(vbox)

        self.SetMaxSize(self.GetSize())

    def GetVersion(self):
        version = f"{Config.APP.version} ({Config.APP.version_code})"

        return version

    def GetDateLabel(self):
        if build_time := os.environ.get("PYSTAND_BUILD_TIME"):
            return _("构建时间：%s") % build_time
        else:
            return _("发布时间：%s") % date
