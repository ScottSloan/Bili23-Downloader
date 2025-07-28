import wx
import wx.html2
from importlib.resources import files

from utils.module.web.page import WebPage

class Webview:
    def __init__(self, parent):
        self.parent = parent

        self.browser = wx.html2.WebView = wx.html2.WebView.New(parent, -1, backend = WebPage.get_webview_backend())

    def get_page(self, file: str):
        try:
            return files("static").joinpath(file).read_text(encoding = "utf-8")

        except FileNotFoundError:
            dlg = wx.MessageDialog(self.parent, f"文件不存在\n\nHTML 静态文件 ({file}) 不存在，无法调用 Webview 进行显示。", "警告", wx.ICON_WARNING)

        except Exception as e:
            dlg = wx.MessageDialog(self.parent, "无法读取静态文件\n\n在读取静态文件时出错", "警告", wx.ICON_WARNING)

        dlg.ShowModal()