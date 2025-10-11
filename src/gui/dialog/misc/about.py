import wx
import os
import wx.adv
import gettext

from utils.config import Config

from utils.common.style.icon_v4 import Icon, IconID, IconSize
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
        Dialog.__init__(self, parent, _("关于 %s") % Config.APP.name)

        self._enale_dark_mode = True

        self.init_UI()


        self.CenterOnParent()

        wx.Bell()
    
    def init_UI(self):
        self.set_dark_mode()

        logo = StaticBitmap(self, bmp = Icon.get_icon_bitmap(IconID.App_Default, IconSize.MEDIUM), size = self.FromDIP((48, 48)))

        font: wx.Font = self.GetFont()
        font.SetFractionalPointSize(int(font.GetFractionalPointSize() + 3))

        app_name_lab = wx.StaticText(self, -1, Config.APP.name)
        app_name_lab.SetFont(font.MakeBold())

        top_vbox = wx.BoxSizer(wx.HORIZONTAL)
        top_vbox.Add(logo, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        top_vbox.Add(app_name_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))

        version_lab = wx.StaticText(self, -1, _("软件版本：%s") % self.GetVersion())
        date_lab = wx.StaticText(self, -1, self.GetDateLabel())
        license_lab = wx.StaticText(self, -1, _("本软件为开源免费软件，在 MIT License 许可协议下进行发布。"))

        homepage_link = URLBox(self, _("官方网站："), "https://bili23.scott-sloan.cn")
        github_link = URLBox(self, _("项目首页："), "https://www.github.com/ScottSloan/Bili23-Downloader")

        body_vbox = wx.BoxSizer(wx.VERTICAL)
        body_vbox.Add(version_lab, 0, wx.ALL, self.FromDIP(6))
        body_vbox.Add(date_lab, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        body_vbox.Add(license_lab, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        body_vbox.Add(homepage_link, 0, wx.ALL, self.FromDIP(6))
        body_vbox.Add(github_link, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))

        copyright_lab = InfoLabel(self, "Copyright © 2022-2025 Scott Sloan")

        opensource_lab = wx.adv.HyperlinkCtrl(self, -1, _("开源许可"), url = "https://bili23.scott-sloan.cn/doc/license.html")
        disclaimer_lab = wx.adv.HyperlinkCtrl(self, -1, _("免责声明"), url = "https://bili23.scott-sloan.cn/doc/announcement.html")

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.Add(opensource_lab, 0, wx.ALL, self.FromDIP(6))
        bottom_hbox.Add(disclaimer_lab, 0, wx.ALL, self.FromDIP(6))

        bottom_vbox = wx.BoxSizer(wx.VERTICAL)
        bottom_vbox.Add(copyright_lab, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM) | wx.CENTER, self.FromDIP(10))
        bottom_vbox.Add(bottom_hbox, 0, wx.CENTER)

        about_vbox = wx.BoxSizer(wx.VERTICAL)
        about_vbox.Add(top_vbox, 0, wx.ALL | wx.CENTER, self.FromDIP(6))
        about_vbox.Add(body_vbox, 0, wx.ALL | wx.EXPAND, self.FromDIP(10))
        about_vbox.Add(bottom_vbox, 0, wx.EXPAND)
        about_vbox.AddSpacer(self.FromDIP(10))

        self.SetSizerAndFit(about_vbox)

    def GetVersion(self):
        version = f"{Config.APP.version} ({Config.APP.version_code})"

        return version

    def GetDateLabel(self):
        if build_time := os.environ.get("PYSTAND_BUILD_TIME"):
            return _("构建时间：%s") % build_time
        else:
            return _("发布时间：%s") % date
