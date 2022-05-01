import wx
import os
import requests
from io import BytesIO
from configparser import RawConfigParser

from gui.login import LoginWindow
from gui.templates import Dialog

from utils.config import Config

class UserWindow(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent, "用户中心", (250, 190))
        
        self.init_ui()
        
        self.Bind_EVT()
            
        self.load_conf()

    def init_ui(self):
        self.uname_lab = wx.StaticText(self.panel, -1, "用户名")
        self.uuid_lab = wx.StaticText(self.panel, -1, "uid: ")

        vbox1 = wx.BoxSizer(wx.VERTICAL)
        vbox1.Add(self.uname_lab, 0, wx.ALL, 10)
        vbox1.Add(self.uuid_lab, 0, wx.ALL & (~wx.TOP), 10)

        self.face_btp = wx.StaticBitmap(self.panel, -1, size = self.FromDIP((50, 50)))

        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        hbox1.Add(self.face_btp, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        hbox1.Add(vbox1, 0, wx.EXPAND)

        self.expire_lab = wx.StaticText(self.panel, -1, "登录有效期：")

        self.login_btn = wx.Button(self.panel, -1, "重新登录", size = self.FromDIP((80, 30)))
        self.logout_btn = wx.Button(self.panel, -1, "退出登录", size = self.FromDIP((80, 30)))

        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        hbox2.AddStretchSpacer(1)
        hbox2.Add(self.login_btn, 0, wx.ALL & (~wx.TOP), 10)
        hbox2.Add(self.logout_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), 10)
        hbox2.AddStretchSpacer(1)

        vbox2 = wx.BoxSizer(wx.VERTICAL)
        vbox2.Add(hbox1, 0, wx.EXPAND)
        vbox2.Add(self.expire_lab, 0, wx.ALL, 10)
        vbox2.Add(hbox2, 0, wx.EXPAND)

        self.panel.SetSizer(vbox2)
    
    def load_conf(self):
        self.uname_lab.SetLabel(Config.user_uname)
        self.uuid_lab.SetLabel("uid: {}".format(Config.user_uuid))

        bitmap = wx.Image(BytesIO(requests.get(Config.user_face).content)).Scale(50, 50)

        self.face_btp.SetBitmap(wx.Bitmap(bitmap, wx.BITMAP_SCREEN_DEPTH))

        self.expire_lab.SetLabel("登录有效期：{}".format(Config.user_expire))

    def Bind_EVT(self):
        self.login_btn.Bind(wx.EVT_BUTTON, self.login_EVT)
        self.logout_btn.Bind(wx.EVT_BUTTON, self.logout_EVT)

    def login_EVT(self, event):
        login_window = LoginWindow(self)
        login_window.ShowWindowModal()

        self.load_conf()
    
    def logout_EVT(self, event):
        conf = RawConfigParser()
        conf.read(os.path.join(os.getcwd(), "config.conf"), encoding = "utf-8")

        Config.user_uuid = Config.user_uname = Config.user_face = Config.user_expire = Config.user_sessdata = ""

        conf.set("user", "uuid", Config.user_uuid)
        conf.set("user", "uname", Config.user_uname)
        conf.set("user", "face", Config.user_face)
        conf.set("user", "expire", Config.user_expire)
        conf.set("user", "sessdata", Config.user_sessdata)

        with open(os.path.join(os.getcwd(), "config.conf"), "w", encoding = "utf-8") as f:
            conf.write(f)
        
        self.Hide()