import wx
import os
import json
import requests
from threading import Thread
from configparser import RawConfigParser

from .templates import Dialog

from utils.config import Config
from utils.tools import get_face_pic, get_level_pic, get_header, get_proxy, remove_files

class UserWindow(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent, "用户中心", (250, 190))
        
        self.init_UI()
        self.Bind_EVT()
        
        self.CenterOnParent()

        self.load_info()

    def init_UI(self):
        
        uname_hbox = wx.BoxSizer(wx.HORIZONTAL)

        self.uname_lab = wx.StaticText(self.panel, -1, "用户名")
        self.level = wx.StaticBitmap(self.panel, -1)

        uname_hbox.Add(self.uname_lab, 0, wx.ALL, 10)
        uname_hbox.Add(self.level, 0, wx.ALL & ~(wx.LEFT), 10)

        
        uname_vbox = wx.BoxSizer(wx.VERTICAL)

        self.uid_lab = wx.StaticText(self.panel, -1, "uid: ")

        uname_vbox.Add(uname_hbox)
        uname_vbox.Add(self.uid_lab, 0, wx.ALL & (~wx.TOP), 10)

        
        info_hbox = wx.BoxSizer(wx.HORIZONTAL)

        self.face = wx.StaticBitmap(self.panel, -1)

        info_hbox.Add(self.face, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        info_hbox.Add(uname_vbox)

        self.expire_lab = wx.StaticText(self.panel, -1, "登录有效期至：")

        
        self.refresh_btn = wx.Button(self.panel, -1, "刷新", size = self.FromDIP((80, 30)))
        self.refresh_btn.SetToolTip("刷新用户信息")

        
        self.logout_btn = wx.Button(self.panel, -1, "注销", size = self.FromDIP((80, 30)))
        self.logout_btn.SetToolTip("注销登录，清除用户信息")

        
        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)

        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(self.refresh_btn, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        bottom_hbox.Add(self.logout_btn, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        bottom_hbox.AddStretchSpacer()

        
        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.vbox.Add(info_hbox, 0, wx.EXPAND)
        self.vbox.Add(self.expire_lab, 0, wx.ALL, 10)
        self.vbox.Add(bottom_hbox, 0, wx.EXPAND)

        
        self.panel.SetSizer(self.vbox)
        
    def load_info(self):
        
        self.uname_lab.SetLabel(Config.user_name)
        self.uid_lab.SetLabel("uid: {}".format(Config.user_uid))

        face = wx.Image(get_face_pic(Config.user_face)).Scale(64, 64)
        self.face.SetBitmap(wx.Bitmap(face, wx.BITMAP_SCREEN_DEPTH))

        level = wx.Image(get_level_pic(Config.user_level)).Scale(32, 16)
        self.level.SetBitmap(wx.Bitmap(level, wx.BITMAP_SCREEN_DEPTH))

        self.expire_lab.SetLabel("登录有效期至：{}".format(Config.user_expire))

        self.vbox.Layout()

        
        self.vbox.Fit(self)
        
    def Bind_EVT(self):
        
        self.logout_btn.Bind(wx.EVT_BUTTON, self.logout_btn_EVT)
        self.refresh_btn.Bind(wx.EVT_BUTTON, self.refresh_btn_EVT)

    @property
    def user_detail_info_url(self):
        
        return "https://api.bilibili.com/x/space/acc/info?mid=" + Config.user_uid

    def get_user_detail_info(self):
        
        info_request = requests.get(self.user_detail_info_url, headers = get_header(), proxies = get_proxy())
        info_json = json.loads(info_request.text)["data"]

        Config.user_name = info_json["name"]
        Config.user_face = info_json["face"]
        Config.user_level = info_json["level"]

        remove_files(Config._res_path, ["face.jpg", "level.png"])

        wx.CallAfter(self.load_info)
        wx.CallAfter(self.Parent.init_userinfo)

        self.Cursor = wx.Cursor(wx.CURSOR_ARROW)

    def refresh_btn_EVT(self, event):
        
        self.Cursor = wx.Cursor(wx.CURSOR_WAIT)
        Thread(target = self.get_user_detail_info).start()

    def logout_btn_EVT(self, event):
        
        
        dlg = wx.MessageDialog(self, "是否注销登录\n\n这将会清除本地保存的用户信息", "确认注销登录", wx.ICON_INFORMATION | wx.YES_NO)
        
        
        if dlg.ShowModal() == wx.ID_NO:
            return

        
        conf = RawConfigParser()
        conf.read(os.path.join(os.getcwd(), "config.conf"), encoding = "utf-8")

        
        Config.user_uid = Config.user_name = Config.user_face = Config.user_expire = Config.user_sessdata = ""

        conf.set("user", "uid", Config.user_uid)
        conf.set("user", "uname", Config.user_name)
        conf.set("user", "face", Config.user_face)
        conf.set("user", "expire", Config.user_expire)
        conf.set("user", "sessdata", Config.user_sessdata)

        
        remove_files(Config._res_path, ["face.jpg", "level.png"])

        
        with open(os.path.join(os.getcwd(), "config.conf"), "w", encoding = "utf-8") as f:
            conf.write(f)
        
        self.Hide()

        self.Parent.init_userinfo()