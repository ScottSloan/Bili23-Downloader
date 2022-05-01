import wx
import os
import time
import datetime
from io import BytesIO
from threading import Thread
from configparser import RawConfigParser

from utils.login import Login
from utils.config import Config

from gui.templates import Dialog

class LoginWindow(Dialog):
    def __init__(self, parent):
        self.parent = parent

        Dialog.__init__(self, parent, "登录", (250, 330))

        self.login = Login()
        
        self.init_controls()
        self.Bind_EVT()

        wait_t = Thread(target = self.wait_scan)
        wait_t.start()

    def init_controls(self):
        self.panel.SetBackgroundColour("white")

        scan_lab = wx.StaticText(self.panel, -1, "扫描二维码登录")
        scan_lab.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, faceName = "微软雅黑"))

        qrcode_bitmap = wx.Image(BytesIO(self.login.get_qrcode_pic())).Scale(200, 200)

        self.qrcode = wx.StaticBitmap(self.panel, -1, wx.Bitmap(qrcode_bitmap, wx.BITMAP_SCREEN_DEPTH))

        self.desc_lab = wx.StaticText(self.panel, -1, "请使用哔哩哔哩客户端扫码登录")

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(scan_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        vbox.Add(self.qrcode, 0, wx.EXPAND)
        vbox.Add(self.desc_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)

        self.panel.SetSizer(vbox)

    def Bind_EVT(self):
        self.Bind(wx.EVT_CLOSE, self.On_close)
    
    def On_close(self, event):
        self.isexit = True
        self.Hide()

    def wait_scan(self):
        self.isscan = self.isexit = False

        while not self.isscan and not self.isexit:
            status = self.login.check_isscan()

            if status[0]: 
                self.isscan = True

            elif not status[0] and status[1] == -2:
                self.desc_lab.SetLabel("二维码已过期")
                self.panel.Layout()

            time.sleep(1)
        
        if status[0]:
            user_info = self.login.get_user_info()
            
            self.save_user_info(user_info)

        self.Hide()
        
    def save_user_info(self, user_info: dict):
        time = datetime.datetime.now() + datetime.timedelta(days = 30)

        conf = RawConfigParser()
        conf.read(os.path.join(os.getcwd(), "config.conf"), encoding = "utf-8")

        Config.user_uuid = user_info["uuid"]
        Config.user_uname = user_info["uname"]
        Config.user_face = user_info["face"]
        Config.user_expire = datetime.datetime.strftime(time, "%Y-%m-%d %H:%M:%S")
        Config.user_sessdata = user_info["sessdata"]

        conf.set("user", "uuid", Config.user_uuid)
        conf.set("user", "uname", Config.user_uname)
        conf.set("user", "face", Config.user_face)
        conf.set("user", "expire", Config.user_expire)
        conf.set("user", "sessdata", Config.user_sessdata)

        with open(os.path.join(os.getcwd(), "config.conf"), "w", encoding = "utf-8") as f:
            conf.write(f)