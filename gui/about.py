import io
import wx
import webbrowser

from utils.config import Config
from utils.icons import get_app_icon_big

from .license import LicenseWindow

class AboutWindow(wx.Dialog):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, -1, f"关于 {Config.APP.name}")

        self.init_UI()

        self.Bind_EVT()

        self.CenterOnParent()

        wx.Bell()
    
    def init_UI(self):
        self.SetBackgroundColour("white")

        image = wx.Image(io.BytesIO(get_app_icon_big()), wx.BITMAP_TYPE_JPEG)
        logo = wx.StaticBitmap(self, -1, image.ConvertToBitmap())

        font: wx.Font = self.GetFont()
        font.SetPointSize(10)

        app_name_lab = wx.StaticText(self, -1, f"{Config.APP.name}")
        app_name_lab.SetFont(font.MakeBold())

        version_lab = wx.StaticText(self, -1, f"{Config.APP.version}")
        version_lab.SetFont(font)

        desc_lab = wx.StaticText(self, -1, "下载 bilibili 视频/番剧/电影/纪录片 等资源")

        date_lab = wx.StaticText(self, -1, f"发布日期：{Config.APP.release_date}")

        copyright_lab = wx.StaticText(self, -1, "Copyright © 2022-2024 Scott Sloan")

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

        self.license_btn = wx.Button(self, -1, "授权")
        self.close_btn = wx.Button(self, wx.ID_CANCEL, "关闭")

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
        webbrowser.open("https://scott-sloan.cn")
