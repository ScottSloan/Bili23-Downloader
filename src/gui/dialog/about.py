import wx
import webbrowser

from utils.config import Config
from utils.common.icon_v2 import IconManager, IconType

from .license import LicenseWindow

class AboutWindow(wx.Dialog):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, -1, f"关于 {Config.APP.name}")

        self.init_UI()

        self.Bind_EVT()

        self.CenterOnParent()

        wx.Bell()
    
    def init_UI(self):
        def _set_dark_mode():
            if not Config.Sys.dark_mode:
                self.SetBackgroundColour("white")

        def _get_scale_size(_size: tuple):
            match Config.Sys.platform:
                case "windows":
                    return self.FromDIP(_size)
                
                case "linux" | "darwin":
                    return wx.DefaultSize

        def _set_icon_background(image: wx.Image):
            _width, _height = image.GetSize()

            if Config.Sys.dark_mode:
                color = self.GetBackgroundColour()

                for x in range(_width):
                    for y in range(_height):
                        r, g, b = image.GetRed(x, y), image.GetGreen(x, y), image.GetBlue(x, y)

                        if r > 200 and g > 200 and b > 200:
                            # 选取背景颜色填充
                            image.SetRGB(x, y, color[0], color[1], color[2])

            return image

        _set_dark_mode()

        icon_manager = IconManager(self)

        logo = wx.StaticBitmap(self, -1, _set_icon_background(icon_manager.get_icon_bitmap(IconType.APP_ICON_DEFAULT)).ConvertToBitmap())

        font: wx.Font = self.GetFont()
        font.SetFractionalPointSize(int(font.GetFractionalPointSize() + 1))

        app_name_lab = wx.StaticText(self, -1, f"{Config.APP.name}")
        app_name_lab.SetFont(font.MakeBold())

        version_lab = wx.StaticText(self, -1, f"{Config.APP.version}")
        version_lab.SetFont(font)

        desc_lab = wx.StaticText(self, -1, "下载 B 站视频/番剧/电影/纪录片 等资源")

        date_lab = wx.StaticText(self, -1, f"发布日期：{Config.APP.release_date} ({Config.APP.version_code})")

        copyright_lab = wx.StaticText(self, -1, "Copyright © 2022-2025 Scott Sloan")

        copyright_hbox = wx.BoxSizer(wx.HORIZONTAL)
        copyright_hbox.AddSpacer(25)
        copyright_hbox.Add(copyright_lab, 0, wx.ALL & (~wx.TOP), 10)
        copyright_hbox.AddSpacer(25)

        self.website_link = wx.StaticText(self, -1, "项目地址")
        self.website_link.SetForegroundColour(wx.Colour(0, 102, 209))
        self.website_link.SetCursor(wx.Cursor(wx.CURSOR_HAND))
        self.website_link.SetFont(copyright_lab.GetFont().MakeUnderlined())

        self.blog_link = wx.StaticText(self, -1, "个人博客")
        self.blog_link.SetForegroundColour(wx.Colour(0, 102, 209))
        self.blog_link.SetCursor(wx.Cursor(wx.CURSOR_HAND))
        self.blog_link.SetFont(copyright_lab.GetFont().MakeUnderlined())

        self.license_btn = wx.Button(self, -1, "授权", size = _get_scale_size((80, 26)))
        self.close_btn = wx.Button(self, wx.ID_CANCEL, "关闭", size = _get_scale_size((80, 26)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.Add(self.license_btn, 0, wx.ALL, 10)
        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(self.close_btn, 0, wx.ALL, 10)

        about_vbox = wx.BoxSizer(wx.VERTICAL)
        about_vbox.Add(logo, 0, wx.ALL | wx.CENTER, 10)
        about_vbox.Add(app_name_lab, 0, wx.ALL & (~wx.BOTTOM) | wx.CENTER, 10)
        about_vbox.Add(version_lab, 0, wx.ALL & (~wx.TOP) | wx.CENTER, 10)
        about_vbox.Add(desc_lab, 0, wx.ALL | wx.CENTER, 10)
        about_vbox.Add(date_lab, 0, wx.ALL | wx.CENTER, 10)
        about_vbox.AddSpacer(20)
        about_vbox.Add(copyright_hbox, 0, wx.EXPAND)
        about_vbox.Add(self.website_link, 0, wx.ALL & (~wx.TOP) | wx.CENTER, 10)
        about_vbox.Add(self.blog_link, 0, wx.ALL & (~wx.TOP) | wx.CENTER, 10)
        about_vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(about_vbox)

    def Bind_EVT(self):
        self.website_link.Bind(wx.EVT_LEFT_DOWN, self.onOpenWebsite)
        self.blog_link.Bind(wx.EVT_LEFT_DOWN, self.onOpenBlog)

        self.license_btn.Bind(wx.EVT_BUTTON, self.onShowLicense)

    def onShowLicense(self, event):
        license_window = LicenseWindow(self)
        license_window.ShowModal()

    def onOpenWebsite(self, event):
        webbrowser.open("https://www.github.com/ScottSloan/Bili23-Downloader")

    def onOpenBlog(self, event):
        webbrowser.open("https://www.scott-sloan.cn")
