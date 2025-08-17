import wx
import json
import wx.html2

from utils.config import Config
from utils.auth.login_v2 import LoginInfo
from utils.common.enums import Platform

from gui.component.window.dialog import Dialog
from gui.component.webview import Webview

class CaptchaDialog(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent, "请完成验证")

        self.init_UI()

        self.SetSize(self.FromDIP((400, 500)))

        self.Bind_EVT()

        self.CenterOnParent()

        self.init_utils()
        
    def init_UI(self):
        self.webview = Webview(self)

        self.webview.get_page("captcha.html")

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.webview.browser, 1, wx.ALL | wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def Bind_EVT(self):
        self.webview.browser.Bind(wx.html2.EVT_WEBVIEW_SCRIPT_MESSAGE_RECEIVED, self.onMessageEVT)

        self.webview.browser.Bind(wx.html2.EVT_WEBVIEW_LOADED, self.onLoadedEVT)

        self.Bind(wx.EVT_CLOSE, self.onCloseEVT)

    def init_utils(self):
        self.webview.browser.AddScriptMessageHandler("MainApplication")

    def onLoadedEVT(self, event):
        self.webview.browser.RunScriptAsync(f"receiveMessage('{LoginInfo.Captcha.gt}','{LoginInfo.Captcha.challenge}')")

    def onMessageEVT(self, event):
        message = event.GetString()

        data = json.loads(message)

        if data["msg"] == "captchaResult":
            LoginInfo.Captcha.validate = data["data"]["validate"]
            LoginInfo.Captcha.seccode = data["data"]["seccode"]

            event = wx.PyCommandEvent(wx.EVT_CLOSE.typeId, self.GetId())
            wx.PostEvent(self.GetEventHandler(), event)

    def onCloseEVT(self, event):
        LoginInfo.Captcha.flag = False

        event.Skip()
