import wx
import json
import requests
from threading import Thread

from .templates import Dialog

from utils.config import Config
from utils.tools import *

class UserWindow(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent, "用户中心", (250, 190))
        
        self.init_UI()
        self.Bind_EVT()
        
        self.CenterOnParent()

        self.load_info()

    @property
    def user_info_url(self):
        return "https://api.bilibili.com/x/web-interface/nav"

    def init_UI(self):
        uname_hbox = wx.BoxSizer(wx.HORIZONTAL)

        self.uname_lab = wx.StaticText(self.panel, -1, "用户名")
        self.uname_lab.SetFont(wx.Font(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, faceName = "微软雅黑")))
        self.level = wx.StaticBitmap(self.panel, -1)
        self.vip_badge = wx.StaticBitmap(self.panel, -1, )

        uname_hbox.Add(self.uname_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        uname_hbox.Add(self.level, 0, wx.ALL & ~(wx.LEFT) | wx.ALIGN_CENTER, 10)
        uname_hbox.Add(self.vip_badge, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, 10)

        uname_vbox = wx.BoxSizer(wx.VERTICAL)

        self.uid_lab = wx.StaticText(self.panel, -1, "UID：")

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
        self.uid_lab.SetLabel("UID：{}".format(Config.user_uid))

        face = wx.Image(get_face_pic(Config.user_face)).Scale(64, 64)
        self.face.SetBitmap(wx.Bitmap(face, wx.BITMAP_SCREEN_DEPTH))

        level = wx.Image(get_level_pic(Config.user_level)).Scale(40, 20)
        self.level.SetBitmap(wx.Bitmap(level, wx.BITMAP_SCREEN_DEPTH))

        if Config.user_vip_status == 0:
            w, h = 60, 25
        else:
            w, h = 69, 20
        
        badge = wx.Image(get_vip_badge_pic(Config.user_vip_badge)).Scale(w, h)
        self.vip_badge.SetBitmap(wx.Bitmap(badge, wx.BITMAP_SCREEN_DEPTH))

        self.expire_lab.SetLabel("登录有效期至：{}".format(Config.user_expire))

        self.vbox.Layout()

        self.vbox.Fit(self)
        
    def Bind_EVT(self):
        self.logout_btn.Bind(wx.EVT_BUTTON, self.logout_btn_EVT)
        self.refresh_btn.Bind(wx.EVT_BUTTON, self.refresh_btn_EVT)

    def refresh_user_info(self):
        from utils.login import QRLogin
        
        login = QRLogin()
        user_info = login.get_user_info(cookie = Config.user_sessdata)

        Config.user_name = user_info["uname"]
        Config.user_face = user_info["face"]
        Config.user_level = user_info["level"]
        Config.user_vip_status = user_info["vip_status"]
        Config.user_vip_badge = user_info["vip_badge"]

        remove_files(Config._res_path, ["face.jpg", "level.png", "badge.png"])

        self.load_info()
        self.Parent.init_userinfo()
        
        Config.set_user_info()

        self.Cursor = wx.Cursor(wx.CURSOR_ARROW)
        
        self.panel.Layout()

    def refresh_btn_EVT(self, event):
        self.Cursor = wx.Cursor(wx.CURSOR_WAIT)
        
        Thread(target = self.refresh_user_info).start()

    def logout_btn_EVT(self, event):
        dlg = wx.MessageDialog(self, "注销登录\n\n是否注销登录并清除本地用户信息？", "注销", wx.ICON_INFORMATION | wx.YES_NO)
        
        if dlg.ShowModal() == wx.ID_NO:
            return

        Config.reset_user_info()

        Config.set_user_info()
        
        remove_files(Config._res_path, ["face.jpg", "level.png", "badge.png"])
        
        self.Hide()

        self.Parent.infobar.ShowMessageInfo(102)
        self.Parent.init_userinfo()
        