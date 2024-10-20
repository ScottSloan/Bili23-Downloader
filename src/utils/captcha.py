import wx
import wx.html
import wx.html2

import os
import json
import ctypes
import requests
import base64
from .captchaPage import CaptchaPage

class WebviewWindow(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, -1, "Captcha", style = wx.DEFAULT_FRAME_STYLE & ~wx.MAXIMIZE_BOX & ~wx.RESIZE_BORDER)

        self.SetSize(self.FromDIP((400, 500)))

        self.init_UI()

        self.Bind_EVT()

        self.CenterOnScreen()

        self.init_utils()
        
    def init_UI(self):
        panel = wx.Panel(self, -1)

        self.webview: wx.html2.WebView = wx.html2.WebView.New(panel, -1, backend = wx.html2.WebViewBackendEdge)

        self.webview.SetPage(base64.b64decode(CaptchaPage.html).decode("utf-8"), "")

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.webview, 1, wx.ALL | wx.EXPAND)

        panel.SetSizerAndFit(vbox)

    def Bind_EVT(self):
        self.webview.Bind(wx.html2.EVT_WEBVIEW_SCRIPT_MESSAGE_RECEIVED, self.onMessage)

        self.webview.Bind(wx.html2.EVT_WEBVIEW_LOADED, self.onLoaded)

    def init_utils(self):
        self.webview.EnableAccessToDevTools(True)

        self.webview.AddScriptMessageHandler("MainApplication")

    def onLoaded(self, event):
        data = self.get_challenge_gt()

        self.webview.RunScriptAsync("receiveMessage('{}','{}')".format(data["gt"], data["challenge"]))

    def onMessage(self, event):
        message = event.GetString()
        message = json.loads(message)
        print(message)

    def get_challenge_gt(self):
        req = requests.get("https://passport.bilibili.com/x/passport-login/captcha?source=main_web", headers = {"User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/129.0.0.0 Safari/537.36 Edg/129.0.0.0"})

        data = json.loads(req.text)

        token = data["data"]["token"]
        challenge = data["data"]["geetest"]["challenge"]
        gt = data["data"]["geetest"]["gt"]

        return {"token": token, "challenge": challenge, "gt": gt}

