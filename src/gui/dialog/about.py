import wx
import webbrowser

from utils.config import Config
from utils.common.icon_v3 import Icon, IconID
from utils.common.compile_data import date, compile

from gui.dialog.license import LicenseWindow
from gui.component.dialog import Dialog

class AboutWindow(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent, f"关于 {Config.APP.name}")

        self._enale_dark_mode = True

        self.init_UI()

        self.Bind_EVT()

        self.CenterOnParent()

        wx.Bell()
    
    def init_UI(self):
        def set_icon_background(image: wx.Image):
            _width, _height = image.GetSize()

            if Config.Sys.dark_mode:
                color = wx.SystemSettings.GetColour(getattr(wx, "SYS_COLOUR_FRAMEBK"))

                for x in range(_width):
                    for y in range(_height):
                        r, g, b = image.GetRed(x, y), image.GetGreen(x, y), image.GetBlue(x, y)

                        if r > 200 and g > 200 and b > 200:
                            # 选取背景颜色填充
                            image.SetRGB(x, y, color[0], color[1], color[2])

            return image

        self.set_dark_mode()

        logo = wx.StaticBitmap(self, -1, set_icon_background(Icon.get_icon_bitmap(IconID.APP_ICON_DEFAULT)).ConvertToBitmap())

        font: wx.Font = self.GetFont()
        font.SetFractionalPointSize(int(font.GetFractionalPointSize() + 1))

        app_name_lab = wx.StaticText(self, -1, f"{Config.APP.name}")
        app_name_lab.SetFont(font.MakeBold())

        version_lab = wx.StaticText(self, -1, f"{Config.APP.version}")
        version_lab.SetFont(font)

        desc_lab = wx.StaticText(self, -1, "下载 B 站视频/番剧/电影/纪录片等资源")

        date_lab = wx.StaticText(self, -1, f"构建日期：{date}" if compile else f"发布日期：{date}")

        copyright_lab = wx.StaticText(self, -1, "Copyright © 2022-2025 Scott Sloan")

        copyright_hbox = wx.BoxSizer(wx.HORIZONTAL)
        copyright_hbox.AddSpacer(self.FromDIP(16))
        copyright_hbox.Add(copyright_lab, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        copyright_hbox.AddSpacer(self.FromDIP(16))

        self.github_link = wx.StaticText(self, -1, "GitHub 主页")
        self.github_link.SetForegroundColour(wx.Colour(0, 102, 209))
        self.github_link.SetCursor(wx.Cursor(wx.CURSOR_HAND))
        self.github_link.SetFont(copyright_lab.GetFont().MakeUnderlined())

        self.home_link = wx.StaticText(self, -1, "项目官网")
        self.home_link.SetForegroundColour(wx.Colour(0, 102, 209))
        self.home_link.SetCursor(wx.Cursor(wx.CURSOR_HAND))
        self.home_link.SetFont(copyright_lab.GetFont().MakeUnderlined())

        self.license_btn = wx.Button(self, -1, "授权", size = self.get_scaled_size((80, 26)))
        self.close_btn = wx.Button(self, wx.ID_CANCEL, "关闭", size = self.get_scaled_size((80, 26)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.Add(self.license_btn, 0, wx.ALL, self.FromDIP(6))
        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(self.close_btn, 0, wx.ALL, self.FromDIP(6))

        about_vbox = wx.BoxSizer(wx.VERTICAL)
        about_vbox.Add(logo, 0, wx.ALL | wx.CENTER, self.FromDIP(6))
        about_vbox.Add(app_name_lab, 0, wx.ALL & (~wx.BOTTOM) | wx.CENTER, self.FromDIP(6))
        about_vbox.Add(version_lab, 0, wx.ALL & (~wx.TOP) | wx.CENTER, self.FromDIP(6))
        about_vbox.Add(desc_lab, 0, wx.ALL | wx.CENTER, self.FromDIP(6))
        about_vbox.Add(date_lab, 0, wx.ALL | wx.CENTER, self.FromDIP(6))
        about_vbox.AddSpacer(self.FromDIP(13))
        about_vbox.Add(copyright_hbox, 0, wx.CENTER)
        about_vbox.Add(self.home_link, 0, wx.ALL & (~wx.TOP) | wx.CENTER, self.FromDIP(6))
        about_vbox.Add(self.github_link, 0, wx.ALL & (~wx.TOP) | wx.CENTER, self.FromDIP(6))
        about_vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(about_vbox)

    def Bind_EVT(self):
        self.github_link.Bind(wx.EVT_LEFT_DOWN, self.onOpenGithubLink)
        self.home_link.Bind(wx.EVT_LEFT_DOWN, self.onOpenHomeLink)

        self.license_btn.Bind(wx.EVT_BUTTON, self.onShowLicense)

    def onShowLicense(self, event):
        license_window = LicenseWindow(self)
        license_window.ShowModal()

    def onOpenGithubLink(self, event):
        webbrowser.open("https://www.github.com/ScottSloan/Bili23-Downloader")

    def onOpenHomeLink(self, event):
        webbrowser.open("https://bili23.scott-sloan.cn/")
