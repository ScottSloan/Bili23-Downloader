import wx
import os
import json
import wx.adv
import gettext
import inspect
import platform

from utils.config import Config

from utils.common.style.icon_v4 import Icon, IconID, IconSize
from utils.common.style.color import Color
from utils.common.enums import Platform
import utils.common.compile_data as json_data

from gui.component.window.dialog import Dialog
from gui.component.staticbitmap.staticbitmap import StaticBitmap

_ = gettext.gettext

class AboutWindow(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent, "")

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

        self.CenterOnParent()

        wx.Bell()
    
    def init_UI(self):
        self.logo = StaticBitmap(self, size = self.FromDIP((64, 64)))

        logo_vbox = wx.BoxSizer(wx.VERTICAL)
        logo_vbox.Add(self.logo, 0, wx.ALL, self.FromDIP(6))

        title_font: wx.Font = self.GetFont()
        title_font.SetFractionalPointSize(int(title_font.GetFractionalPointSize() + 4))

        version_font: wx.Font = self.GetFont()
        version_font.SetFractionalPointSize(int(version_font.GetFractionalPointSize() + 2))

        title_lab = wx.StaticText(self, -1, Config.APP.name)
        title_lab.SetForegroundColour(Color.get_frame_text_color())
        title_lab.SetFont(title_font.MakeBold())

        desc_lab = wx.StaticText(self, -1, _("跨平台的 B 站视频下载工具"))
        desc_lab.SetForegroundColour(Color.get_frame_text_color())

        self.version_lab = wx.StaticText(self, -1, _("版本 %s") % self.get_version_str())
        self.version_lab.SetFont(version_font)
        self.version_lab.SetForegroundColour(Color.get_frame_text_color())

        license_lab = wx.StaticText(self, -1, _("本程序为免费开源软件，遵循 MIT 许可证发布"))
        license_lab.SetForegroundColour(Color.get_frame_text_color())

        copyright_lab = wx.StaticText(self, -1, "Copyright © 2022-2025 Scott Sloan. All rights reserved.")
        copyright_lab.SetForegroundColour(Color.get_frame_text_color())

        homepage_link = wx.adv.HyperlinkCtrl(self, -1, _("官方网站"), url = "https://bili23.scott-sloan.cn")
        github_link = wx.adv.HyperlinkCtrl(self, -1, _("开源地址"), url = "https://www.github.com/ScottSloan/Bili23-Downloader")

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
        body_vbox.AddSpacer(self.FromDIP(10))
        body_vbox.Add(self.version_lab, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        body_vbox.Add(license_lab, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM), self.FromDIP(6))
        body_vbox.Add(copyright_lab, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM), self.FromDIP(6))
        body_vbox.Add(link_hbox, 0, wx.EXPAND)
        body_vbox.AddSpacer(self.FromDIP(6))
        body_vbox.Add(btn_hbox, 0, wx.EXPAND)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(logo_vbox, 0, wx.EXPAND, self.FromDIP(6))
        hbox.AddSpacer(self.FromDIP(15))
        hbox.Add(body_vbox, 0, wx.EXPAND, self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.AddSpacer(self.FromDIP(20) if Platform(Config.Sys.platform) != Platform.Windows else 1)
        vbox.Add(hbox, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(20))

        self.SetSizerAndFit(vbox)

        self.SetMaxSize(self.GetSize())

        self.set_dark_mode()

    def Bind_EVT(self):
        self.version_lab.Bind(wx.EVT_LEFT_DOWN, self.show_extra_info)

    def init_utils(self):
        def worker():
            self.logo.SetBitmap(bmp = Icon.get_icon_bitmap(IconID.App_Default, IconSize.LARGE))

            self.Refresh()

        wx.CallAfter(worker)

        if not self.DWMExtendFrameIntoClientArea():
            self.SetTitle(_("关于 %s") % Config.APP.name)

    def get_version_str(self):
        version = f"{Config.APP.version} ({Config.APP.version_code})"

        return version
    
    def show_extra_info(self, event: wx.MouseEvent):
        extra_data = json.loads(inspect.getsource(json_data))

        data = {
            "Platform": Platform(Config.Sys.platform).name,
            "Architecture": platform.machine(),
            "Commit": extra_data.get("commit", "N/A"),
            "Channel": extra_data.get("channel", "N/A"),
            "Date": extra_data.get("date", "N/A")
        }

        wx.MessageDialog(self, "Bili23 Downloader\n\n{}".format("\n".join(f"{key}: {value}" for key, value in data.items())), "info", wx.ICON_INFORMATION).ShowModal()
