import wx
import os
import datetime
from io import BytesIO
from configparser import RawConfigParser

from utils.login import Login
from utils.config import Config

from .templates import Dialog

class LoginWindow(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent, "登录", (250, 330))
        
        self.init_login()

        self.init_UI()
        self.Bind_EVT()

        self.CenterOnParent()

    def init_login(self):
        self.login = Login()

        self.timer = wx.Timer(self, -1)
        self.timer.Start(1000)

    def init_UI(self):
        self.panel.SetBackgroundColour("white")

        scan_lab = wx.StaticText(self.panel, -1, "扫描二维码登录")
        scan_lab.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, faceName = "微软雅黑"))

        qrcode = wx.Image(BytesIO(self.login.get_qrcode_pic())).Scale(200, 200)

        self.qrcode = wx.StaticBitmap(self.panel, -1, wx.Bitmap(qrcode, wx.BITMAP_SCREEN_DEPTH))

        self.lab = wx.StaticText(self.panel, -1, "请使用哔哩哔哩客户端扫码登录")

        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.vbox.Add(scan_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        self.vbox.Add(self.qrcode, 0, wx.EXPAND)
        self.vbox.Add(self.lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)

        self.panel.SetSizer(self.vbox)

        self.vbox.Fit(self)
        
    def Bind_EVT(self):
        self.Bind(wx.EVT_CLOSE, self.onClose)

        self.Bind(wx.EVT_TIMER, self.onTimer, self.timer)
    
    def onClose(self, event):
        self.timer.Stop()

        event.Skip()

    def onTimer(self, event):
        json = self.login.check_scan()

        if json["status"]:  
            self.save_user_info(self.login.get_user_info())

            self.Hide()

            wx.CallAfter(self.Parent.init_userinfo)

        elif not json["status"] and json["code"] == -2:
            wx.CallAfter(self.refresh_qrcode)
    
    def refresh_qrcode(self):
        self.login = Login()

        qrcode = wx.Image(BytesIO(self.login.get_qrcode_pic())).Scale(200, 200)

        self.qrcode.SetBitmap(wx.Bitmap(qrcode, wx.BITMAP_SCREEN_DEPTH))

    def save_user_info(self, user_info: dict):
        time = datetime.datetime.now() + datetime.timedelta(days = 30)

        conf = RawConfigParser()
        conf.read(os.path.join(os.getcwd(), "config.conf"), encoding = "utf-8")

        Config.user_uid = user_info["uid"]
        Config.user_name = user_info["uname"]
        Config.user_face = user_info["face"]
        Config.user_level = user_info["level"]
        Config.user_expire = datetime.datetime.strftime(time, "%Y-%m-%d %H:%M:%S")
        Config.user_sessdata = user_info["sessdata"]

        conf.set("user", "uid", Config.user_uid)
        conf.set("user", "uname", Config.user_name)
        conf.set("user", "face", Config.user_face)
        conf.set("user", "level", Config.user_level)
        conf.set("user", "expire", Config.user_expire)
        conf.set("user", "sessdata", Config.user_sessdata)

        with open(os.path.join(os.getcwd(), "config.conf"), "w", encoding = "utf-8") as f:
            conf.write(f)
            