import wx
from typing import Dict
from io import BytesIO

import wx.adv

from utils.login import QRLogin
from utils.config import Config, conf
from utils.tools import get_background_color
from utils.login import PasswordLogin

from gui.captcha_validate import CaptchaWindow

class LoginWindow(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, "扫码登录")
        
        self.init_login()

        self.init_UI()

        self.Bind_EVT()

        self.CenterOnParent()

    def init_UI(self):
        font: wx.Font = self.GetFont()

        scan_lab = wx.StaticText(self, -1, "扫描二维码登录")
        font.SetPointSize(12)
        scan_lab.SetFont(font)

        self.qrcode = wx.StaticBitmap(self, -1, wx.Image(BytesIO(self.login.get_qrcode())).Scale(250, 250).ConvertToBitmap())

        self.lab = wx.StaticText(self, -1, "请使用哔哩哔哩客户端扫码登录")
        font.SetPointSize(10)
        self.lab.SetFont(font)

        qrcode_vbox = wx.BoxSizer(wx.VERTICAL)
        qrcode_vbox.Add(scan_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        qrcode_vbox.Add(self.qrcode, 0, wx.EXPAND)
        qrcode_vbox.Add(self.lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)

        self.note = wx.Simplebook(self, -1)

        self.note.AddPage(PasswordPage(self.note), "账号密码登录")
        # self.note.AddPage(SMSPage(self.note), "手机号登录")

        note_vbox = wx.BoxSizer(wx.VERTICAL)
        note_vbox.AddStretchSpacer()
        note_vbox.Add(self.note, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        note_vbox.AddStretchSpacer()

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(qrcode_vbox, 0, wx.EXPAND)
        hbox.Add(note_vbox, 0, wx.EXPAND)

        self.SetSizerAndFit(hbox)

        self.SetBackgroundColour(get_background_color())

    def init_login(self):
        self.login = QRLogin()
        self.login.init_qrcode()

        self.timer = wx.Timer(self, -1)
        self.timer.Start(1000)

    def Bind_EVT(self):
        self.Bind(wx.EVT_CLOSE, self.onClose)

        self.Bind(wx.EVT_TIMER, self.onTimer, self.timer)

    def onClose(self, event):
        self.timer.Stop()

        event.Skip()

    def onTimer(self, event):
        match self.login.check_scan()["code"]:
            case 0:
                user_info = self.login.get_user_info()
                
                self.login_success(user_info)

            case 86090:
                self.lab.SetLabel("请在设备侧确认登录")
                self.Layout()

            case 86038:
                wx.CallAfter(self.refresh_qrcode)
    
    def init_userinfo(self):
        self.timer.Stop()
        
        self.GetParent().init_user_info()
        self.GetParent().infobar.ShowMessage("提示：登录成功", flags = wx.ICON_INFORMATION)

        # 重新创建主窗口菜单
        self.GetParent().init_menubar()

    def refresh_qrcode(self):
        self.login = QRLogin()
        self.login.init_qrcode()

        self.lab.SetLabel("请使用哔哩哔哩客户端扫码登录")
        self.qrcode.SetBitmap(wx.Image(BytesIO(self.login.get_qrcode())).Scale(250, 250).ConvertToBitmap())

        self.Layout()

    def save_user_info(self, user_info: Dict):
        Config.User.login = True

        Config.User.face = user_info["face"]
        Config.User.uname = user_info["uname"]
        Config.User.sessdata = user_info["sessdata"]

        conf.save_all_user_config()

    def login_success(self, user_info):
        self.save_user_info(user_info)

        self.Hide()

        wx.CallAfter(self.init_userinfo)

class PasswordPage(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

    def init_UI(self):
        username_lab = wx.StaticText(self, -1, "账号")
        self.username_box = wx.TextCtrl(self, -1, size = self.FromDIP((200, 26)))

        username_hbox = wx.BoxSizer(wx.HORIZONTAL)
        username_hbox.Add(username_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        username_hbox.Add(self.username_box, 0, wx.ALL & (~wx.LEFT), 10)

        password_lab = wx.StaticText(self, -1, "密码")
        self.password_box = wx.TextCtrl(self, -1, size = self.FromDIP((200, 26)), style = wx.TE_PASSWORD)

        password_hbox = wx.BoxSizer(wx.HORIZONTAL)
        password_hbox.Add(password_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        password_hbox.Add(self.password_box, 0, wx.ALL & (~wx.LEFT), 10)

        self.login_btn = wx.Button(self, -1, "登录", size = self.FromDIP((120, 30)))

        login_hbox = wx.BoxSizer(wx.HORIZONTAL)
        login_hbox.AddStretchSpacer()
        login_hbox.Add(self.login_btn, 0, wx.ALL, 10)
        login_hbox.AddStretchSpacer()

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(username_hbox, 0, wx.EXPAND)
        vbox.Add(password_hbox, 0, wx.EXPAND)
        vbox.Add(login_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

        self.SetBackgroundColour(get_background_color())

    def Bind_EVT(self):
        self.login_btn.Bind(wx.EVT_BUTTON, self.onLogin)

    def init_utils(self):
        self.is_captcha_passed = False

        self.login = PasswordLogin()

    def onLogin(self, event):
        # 判断是否通过极验 captcha
        if not self.is_captcha_passed:
            captcha_window = CaptchaWindow(self)
            captcha_window.ShowModal()

        # 获取公钥
        self.login.get_public_key()

        # 将密码进行加盐加密
        password_encrypt = self.login.encrypt_password(self.password_box.GetValue())
        username = self.username_box.GetValue()

        # 进行登录操作
        result = self.login.login(username, password_encrypt)

        self.check_login_result(result)

    def check_login_result(self, result):
        if result["code"] != 0:
            wx.MessageDialog(self, f"登录失败\n\n登录失败，原因：{result['message']} ({result['code']})", "警告", wx.ICON_WARNING).ShowModal()

        else:
            if result["data"]["status"] != 0:
                wx.MessageDialog(self, f"登录失败\n\n登录失败，原因：{result['data']['message']} ({result['data']['status']})", "警告", wx.ICON_WARNING).ShowModal()

                return

            # 登录成功，关闭窗口
            user_info = self.login.get_user_info()

            self.GetParent().login_success(user_info)