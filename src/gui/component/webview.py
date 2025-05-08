import wx
import os

from utils.common.enums import Platform
from utils.config import Config

class Webview:
    def __init__(self, parent):
        self.parent = parent

        backend = self.check_webview_backend()

        self.browser = wx.html2.WebView = wx.html2.WebView.New(parent, -1, backend = backend)

    def check_webview_backend(self):
        def get_webview_backend():
            match Platform(Config.Sys.platform):
                case Platform.Windows:
                    return wx.html2.WebViewBackendEdge
                
                case Platform.Linux | Platform.macOS:
                    return wx.html2.WebViewBackendWebKit

        try:
            import wx.html2

            backend = get_webview_backend()

            if not wx.html2.WebView.IsBackendAvailable(backend):
                raise RuntimeError("Webview is unavailable")

        except:
            wx.MessageDialog(self, f"WebView 不可用\n\n未找到可用的 WebView 环境，无法进行人机验证，请使用扫码登录。\n\n详细解决方案请参考程序说明文档", "警告", wx.ICON_WARNING).ShowModal()

        return backend
    
    def get_page(self, file: str):
        def get_file_path(*paths):
            return os.path.join(os.getcwd(), *paths)
        
        possible_paths = [get_file_path("src", "static", file), get_file_path("static", file)]

        for path in possible_paths:
            if os.path.exists(path):
                with open(path, "r", encoding = "utf-8") as f:
                    return f.read()
                
        wx.MessageDialog(self.parent, "文件不存在\n\nHTML 静态文件不存在，无法调用 Webview 显示。", "警告", wx.ICON_WARNING).ShowModal()

        self.parent.Destroy()