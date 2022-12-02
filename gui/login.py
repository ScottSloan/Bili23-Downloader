import wx
import wx.adv
import datetime
from io import BytesIO

from utils.login import QRLogin
from utils.config import Config
from utils.tools import *

from .templates import Dialog

class LoginWindow(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent, "登录", (250, 330))
        
        self.init_login()

        self.init_UI()
        self.Bind_EVT()

        self.CenterOnParent()

    @property
    def user_info_url(self):
        return "https://api.bilibili.com/x/web-interface/nav"

    def init_login(self):
        self.login = QRLogin()
        self.login.init_qrcode()

        self.timer = wx.Timer(self, -1)
        self.timer.Start(1000)

    def init_UI(self):
        self.panel.SetBackgroundColour("white")

        scan_lab = wx.StaticText(self.panel, -1, "扫描二维码登录")
        scan_lab.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, faceName = "微软雅黑"))

        qrcode = wx.Image(BytesIO(self.login.get_qrcode_pic())).Scale(200, 200)

        self.qrcode = wx.StaticBitmap(self.panel, -1, wx.Bitmap(qrcode, wx.BITMAP_SCREEN_DEPTH))

        self.lab = wx.StaticText(self.panel, -1, "请使用哔哩哔哩客户端扫码登录")
        self.lab.SetFont(wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, faceName = "微软雅黑"))

        self.cookie_link = wx.adv.HyperlinkCtrl(self.panel, -1, "使用 Cookie 登录", "使用 Cookie 登录")

        self.vbox = wx.BoxSizer(wx.VERTICAL)
        self.vbox.Add(scan_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        self.vbox.Add(self.qrcode, 0, wx.EXPAND)
        self.vbox.Add(self.lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        self.vbox.Add(self.cookie_link, 0, wx.ALL | wx.ALIGN_CENTER, 10)

        self.panel.SetSizer(self.vbox)

        self.vbox.Fit(self)
        
    def Bind_EVT(self):
        self.Bind(wx.EVT_CLOSE, self.onClose)

        self.Bind(wx.EVT_TIMER, self.onTimer, self.timer)

        self.cookie_link.Bind(wx.adv.EVT_HYPERLINK, self.hyperlink_EVT)

    def onClose(self, event):
        self.timer.Stop()

        event.Skip()

    def onTimer(self, event):
        json = self.login.check_scan()

        if json["code"] == 0:
            user_info = self.login.get_user_info(session = True)
            self.save_user_info(user_info)

            self.Hide()

            Config.user_login = True
            
            wx.CallAfter(self.init_userinfo)

        elif json["code"] == 86090:
            self.lab.SetLabel("请在设备侧确认登录")
            self.vbox.Layout()

        elif json["code"] == 86038:
            wx.CallAfter(self.refresh_qrcode)
    
    def init_userinfo(self):
        self.Parent.infobar.ShowMessageInfo(101)
        self.Parent.init_userinfo()

    def refresh_qrcode(self):
        self.login = QRLogin()

        qrcode = wx.Image(BytesIO(self.login.get_qrcode_pic())).Scale(200, 200)

        self.qrcode.SetBitmap(wx.Bitmap(qrcode, wx.BITMAP_SCREEN_DEPTH))

        self.panel.Layout()

    def hyperlink_EVT(self, event):
        dlg = wx.TextEntryDialog(self.panel, "请将 Cookie SESSDATA 字段粘贴至此", "Cookie 登录")

        if dlg.ShowModal() == wx.ID_OK:
            self.cookie = dlg.GetValue()

            if self.cookie != "":
                try:
                    user_info = self.login.get_user_info(cookie = self.cookie)

                    self.save_user_info(user_info)

                    wx.CallAfter(self.init_userinfo)
                    
                    self.timer.Stop()
                    self.Destroy()
                except:
                    wx.MessageDialog(self, "登录失败\n\n使用 Cookie 登录失败，可能的原因：\n\n1. Cookie 错误\n2. Cookie 过期", "错误", wx.ICON_WARNING).ShowModal()

    def save_user_info(self, user_info: dict):
        time = datetime.datetime.now() + datetime.timedelta(days = 180)

        remove_files(Config._res_path, ["face.jpg", "level.png", "badge.png"])
        
        Config.user_login = True
        Config.user_uid = user_info["uid"]
        Config.user_name = user_info["uname"]
        Config.user_face = user_info["face"]
        Config.user_level = user_info["level"]
        Config.user_expire = datetime.datetime.strftime(time, "%Y-%m-%d %H:%M:%S")
        Config.user_vip_status = user_info["vip_status"]
        Config.user_vip_badge = user_info["vip_badge"]
        Config.user_sessdata = user_info["sessdata"]

        Config.set_user_info()
