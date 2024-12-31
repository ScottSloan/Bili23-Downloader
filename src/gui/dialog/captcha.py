import wx
import wx.html
import wx.html2
import json
import base64

from utils.captcha import CaptchaPage
from utils.auth.login import CaptchaUtils, CaptchaInfo
from utils.config import Config

class CaptchaWindow(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, "请完成验证")

        self.init_UI()

        self.SetSize(self.FromDIP((400, 500)))

        self.Bind_EVT()

        self.CenterOnScreen()

        self.init_utils()
        
    def init_UI(self):
        # 初始化 WebView
        backend = self.get_webview_backend()

        # 检查 webview 可用性
        self.check_webview_backend(backend)
        
        self.webview: wx.html2.WebView = wx.html2.WebView.New(self, -1, backend = backend)

        self.webview.SetPage(base64.b64decode(CaptchaPage.html).decode("utf-8"), "")

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.webview, 1, wx.ALL | wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def Bind_EVT(self):
        self.webview.Bind(wx.html2.EVT_WEBVIEW_SCRIPT_MESSAGE_RECEIVED, self.onMessage)

        self.webview.Bind(wx.html2.EVT_WEBVIEW_LOADED, self.onLoaded)

    def init_utils(self):
        self.captcha = CaptchaUtils()
        
        # 设置 MessageHandler，便于接收从前端返回的验证结果
        self.webview.AddScriptMessageHandler("MainApplication")

    def onLoaded(self, event):
        # 获取极验 captcha 的 gt 和 challenge
        self.captcha.get_geetest_challenge_gt()

        # 向前端传递 gt 和 challenge
        self.webview.RunScriptAsync(f"receiveMessage('{CaptchaInfo.gt}','{CaptchaInfo.challenge}')")

    def onMessage(self, event):
        # 接收前端返回的验证结果
        message = event.GetString()

        data = json.loads(message)

        if data["code"] == 200:
            CaptchaInfo.validate = data["data"]["validate"]
            CaptchaInfo.seccode = data["data"]["seccode"]

            # 验证通过，关闭窗口
            self.webview.Close()
            
            self.Close()
            self.Destroy()

    def get_webview_backend(self):
        # 根据不同平台，使用不同的 webview
        match Config.Sys.platform:
            case "windows":
                # Windows 下使用 Edge Webview2 (需要系统安装)
                backend = wx.html2.WebViewBackendEdge
            
            case "linux" | "darwin":
                # Linux 和 macOS 使用 Webkit
                backend = wx.html2.WebViewBackendWebKit

        return backend
    
    def check_webview_backend(self, backend):
        if not wx.html2.WebView.IsBackendAvailable(backend):
            match Config.Sys.platform:
                case "windows":
                    msg = "Windows 平台：请安装 Microsoft Edge WebView2 Runtime"

                case "linux":
                    msg = "Linux 平台：请安装 WebKitGTK+，例如 Ubuntu 执行 sudo apt install libwebkit2gtk-4.0-dev 进行安装"

            # macOS 系统使用的是 Apple WKWebView，系统自带。

            wx.MessageDialog(self, f"WebView 不可用\n\n未找到可用的 WebView 环境，无法进行人机验证，请使用扫码登录。\n\n解决方案：\n{msg}", "警告", wx.ICON_WARNING).ShowModal()

            # 销毁窗口
            self.Destroy()
