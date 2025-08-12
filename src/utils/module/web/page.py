import wx
import wx.html2
import webbrowser
from importlib.resources import files, as_file

from utils.config import Config
from utils.auth.login_v2 import LoginInfo
from utils.common.enums import Platform, WebPageOption
from utils.common.regex import Regex

from utils.module.web.ws import WebSocketServer

class WebPage:
    @classmethod
    def get_webview_availability(cls):
        return wx.html2.WebView.IsBackendAvailable(cls.get_webview_backend())
    
    @classmethod
    def show_webpage(cls, parent: wx.Window, file_name: str):
        match WebPageOption(Config.Advanced.webpage_option):
            case WebPageOption.Auto:
                if cls.get_webview_availability():
                    cls.webview(parent, file_name)
                else:
                    cls.websocket(parent, file_name)

            case WebPageOption.Webview:
                def worker():
                    if dlg.ShowModal() == wx.ID_YES:
                        Config.Advanced.webpage_option = WebPageOption.Websocket.value

                        cls.show_webpage(parent, file_name)
                    else:
                        LoginInfo.Captcha.flag = False

                if not cls.get_webview_availability():
                    LoginInfo.Captcha.flag = True

                    dlg = wx.MessageDialog(parent, "Webview 不可用\n\n未找到可用的 Webview 组件，无法显示 Web 页面。", "警告", wx.ICON_WARNING | wx.YES_NO)
                    dlg.SetYesNoLabels("使用外部浏览器显示", "取消")

                    wx.CallAfter(worker)

                    return
                
                cls.webview(parent, file_name)

            case WebPageOption.Websocket:
                cls.websocket(parent, file_name)
    
    @staticmethod
    def get_webview_backend():
        match Platform(Config.Sys.platform):
            case Platform.Windows:
                return wx.html2.WebViewBackendEdge
            
            case Platform.Linux | Platform.macOS:
                return wx.html2.WebViewBackendWebKit
            
    @staticmethod
    def webview(parent: wx.Window, file_name: str):
        match file_name:
            case "captcha.html":
                def worker():
                    from gui.dialog.login.captcha import CaptchaDialog

                    dlg = CaptchaDialog(parent)
                    dlg.ShowModal()

                LoginInfo.Captcha.flag = True

                wx.CallAfter(worker)

            case "graph.html":
                def worker():
                    from gui.window.graph import GraphWindow

                    window = GraphWindow(parent)
                    window.Show()

                wx.CallAfter(worker)

    @classmethod
    def websocket(cls, parent: wx.Window, file_name: str):
        websocket = WebSocketServer()
        websocket.start()

        match file_name:
            case "captcha.html":
                LoginInfo.Captcha.flag = True

            case "graph.html":
                pass

        path = cls.get_static_file_path(file_name)

        cls.update_ws_port(path)

        webbrowser.open(f"file://{path}")

    @staticmethod
    def get_static_file_path(file_name: str):
        resource = files("static").joinpath(file_name)

        with as_file(resource) as path:
            return path.resolve()
        
    @staticmethod
    def update_ws_port(file_path: str):
        with open(file_path, "r", encoding = "utf-8") as f:
            contents = Regex.sub(r"port = ([0-9]+)", f"port = {Config.Advanced.websocket_port}", f.read())

        with open(file_path, "w", encoding = "utf-8") as f:
            f.write(contents)
