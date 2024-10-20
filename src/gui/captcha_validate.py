import wx
import wx.html
import wx.html2
import json
import base64

from utils.captcha_page import CaptchaPage
from utils.login import CaptchaUtils, CaptchaInfo

class CaptchaWindow(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, "请完成验证")

        self.init_UI()

        self.SetSize(self.FromDIP((400, 500)))

        self.Bind_EVT()

        self.CenterOnScreen()

        self.init_utils()
        
    def init_UI(self):
        self.webview: wx.html2.WebView = wx.html2.WebView.New(self, -1, backend = wx.html2.WebViewBackendEdge)

        self.webview.SetPage(base64.b64decode(CaptchaPage.html).decode("utf-8"), "")

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.webview, 1, wx.ALL | wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def Bind_EVT(self):
        self.webview.Bind(wx.html2.EVT_WEBVIEW_SCRIPT_MESSAGE_RECEIVED, self.onMessage)

        self.webview.Bind(wx.html2.EVT_WEBVIEW_LOADED, self.onLoaded)

    def init_utils(self):
        self.captcha = CaptchaUtils()

        self.webview.EnableAccessToDevTools(True)

        self.webview.AddScriptMessageHandler("MainApplication")

    def onLoaded(self, event):
        # 获取极验 captcha 的 gt 和 challenge
        self.captcha.get_geetest_challenge_gt()

        # 向前端传递 gt 和 challenge
        self.webview.RunScriptAsync(f"receiveMessage('{CaptchaInfo.gt}','{CaptchaInfo.challenge}')")

    def onMessage(self, event):
        message = event.GetString()

        data = json.loads(message)

        if data["code"] == 200:
            CaptchaInfo.validate = data["data"]["validate"]
            CaptchaInfo.seccode = data["data"]["seccode"]

            # 验证通过，关闭窗口
            self.Destroy()