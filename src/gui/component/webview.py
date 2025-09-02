import wx

from utils.config import Config
from utils.common.enums import Platform
from utils.common.exception import GlobalException, show_error_message_dialog

from utils.module.web.page import WebPage

class Webview:
    def __init__(self, parent):
        self.parent = parent

        import wx.html2

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
            raise GlobalException(callback = self.onError) from e

    def osx_get_page(self, path: str):
        with open(path, "r", encoding = "utf-8") as f:
            return f.read()
        
    def onError(self):
        show_error_message_dialog("无法读取静态文件", "在读取静态文件时出错")