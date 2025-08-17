import wx
import wx.html2

from utils.config import Config
from utils.common.enums import Platform

from utils.module.web.page import WebPage

class Webview:
    def __init__(self, parent):
        self.parent = parent

        self.browser = wx.html2.WebView = wx.html2.WebView.New(parent, -1, backend = WebPage.get_webview_backend())

    def get_page(self, file_name: str):
        try:
            path = WebPage.get_static_file_path(file_name)

            match Platform(Config.Sys.platform):
                case Platform.Windows | Platform.Linux:
                    self.browser.LoadURL(f"file://{path}")

                case Platform.macOS:
                    self.browser.SetPage(self.osx_get_page(path), "")

        except FileNotFoundError:
            dlg = wx.MessageDialog(self.parent, f"文件不存在\n\nHTML 静态文件 ({file_name}) 不存在，无法调用 Webview 进行显示。", "警告", wx.ICON_WARNING)

            dlg.ShowModal()

        except Exception as e:
            dlg = wx.MessageDialog(self.parent, "无法读取静态文件\n\n在读取静态文件时出错", "警告", wx.ICON_WARNING)

            dlg.ShowModal()

    def osx_get_page(self, path: str):
        with open(path, "r", encoding = "utf-8") as f:
            return f.read()
