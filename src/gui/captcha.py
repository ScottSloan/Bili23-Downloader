import wx
import wx.html
import wx.html2
import json
import base64

from utils.captcha import CaptchaPage
from utils.login import CaptchaUtils, CaptchaInfo
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
        self.webview: wx.html2.WebView = wx.html2.WebView.New(self, -1, backend = self.get_webview_backend())

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
            self.Destroy()

    def get_webview_backend(self):
        # 根据不同平台，使用不同的 webview
        match Config.Sys.platform:
            case "windows":
                # Windows 下使用 Edge Webview2 (需要系统安装)
                return wx.html2.WebViewBackendEdge
            
            case "linux" | "darwin":
                # Linux 和 macOS 使用 Webkit
                return wx.html2.WebViewBackendWebKit