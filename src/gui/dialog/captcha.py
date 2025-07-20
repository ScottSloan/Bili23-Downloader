import wx
import json

from utils.auth.login import CaptchaUtils, LoginInfo

from gui.component.window.dialog import Dialog
from gui.component.webview import Webview

class CaptchaWindow(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent, "请完成验证")

        self.init_UI()

        self.SetSize(self.FromDIP((400, 500)))

        self.Bind_EVT()

        self.CenterOnParent()

        self.init_utils()
        
    def init_UI(self):
        self.webview = Webview(self)

        page = self.webview.get_page("captcha.html")

        if not page:
            return

        self.webview.browser.SetPage(page, "")

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.webview.browser, 1, wx.ALL | wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def Bind_EVT(self):
        self.webview.browser.Bind(wx.html2.EVT_WEBVIEW_SCRIPT_MESSAGE_RECEIVED, self.onMessageEVT)

        self.webview.browser.Bind(wx.html2.EVT_WEBVIEW_LOADED, self.onLoadedEVT)

    def init_utils(self):
        self.captcha = CaptchaUtils()
        
        # 设置 MessageHandler，便于接收从前端返回的验证结果
        self.webview.browser.AddScriptMessageHandler("MainApplication")

    def onLoadedEVT(self, event):
        # 获取极验 captcha 的 gt 和 challenge
        self.captcha.get_geetest_challenge_gt()

        # 向前端传递 gt 和 challenge
        self.webview.browser.RunScriptAsync(f"receiveMessage('{LoginInfo.gt}','{LoginInfo.challenge}')")

    def onMessageEVT(self, event):
        # 接收前端返回的验证结果
        message = event.GetString()

        data = json.loads(message)

        if data["code"] == 200:
            LoginInfo.validate = data["data"]["validate"]
            LoginInfo.seccode = data["data"]["seccode"]

            # 验证通过，关闭窗口
            self.webview.browser.Close()
            
            self.Close()
            self.Destroy()
