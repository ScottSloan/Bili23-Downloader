import wx
import time
import requests
from typing import Dict, Callable
from io import BytesIO

from utils.auth.login import QRLogin, PasswordLogin, SMSLogin
from utils.config import Config, ConfigUtils
from utils.common.thread import Thread

from gui.dialog.captcha import CaptchaWindow

class LoginWindow(wx.Dialog):
    def __init__(self, parent, callback: Callable):
        self.callback = callback

        wx.Dialog.__init__(self, parent, -1, "登录")
        
        self.init_utils()

        self.init_UI()

        self.Bind_EVT()

        self.CenterOnParent()

    def init_UI(self):
        def _set_dark_mode():
            if not Config.Sys.dark_mode:
                self.SetBackgroundColour("white")

        _set_dark_mode()

        font: wx.Font = self.GetFont()
        font.SetFractionalPointSize(int(font.GetFractionalPointSize() + 3))

        scan_lab = wx.StaticText(self, -1, "扫描二维码登录")
        scan_lab.SetFont(font)

        self.qrcode = wx.StaticBitmap(self, -1, wx.Image(BytesIO(self.login.get_qrcode())).Scale(250, 250).ConvertToBitmap())

        font: wx.Font = self.GetFont()
        font.SetFractionalPointSize(int(font.GetFractionalPointSize() + 1))

        self.lab = wx.StaticText(self, -1, "请使用哔哩哔哩客户端扫码登录")
        self.lab.SetFont(font)

        qrcode_vbox = wx.BoxSizer(wx.VERTICAL)
        qrcode_vbox.Add(scan_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        qrcode_vbox.Add(self.qrcode, 0, wx.EXPAND)
        qrcode_vbox.Add(self.lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)

        self.note = wx.Simplebook(self, -1)

        password_page = PasswordPage(self.note, self.session)
        password_page.get_finger_spi()

        self.note.AddPage(password_page, "账号密码登录")
        self.note.AddPage(SMSPage(self.note, self.session), "手机号登录")

        font: wx.Font = self.GetFont()
        font.SetFractionalPointSize(int(font.GetFractionalPointSize() + 3))

        self.password_login_btn = wx.StaticText(self, -1, "密码登录")
        self.password_login_btn.SetForegroundColour(wx.Colour(79, 165, 217))
        self.password_login_btn.SetFont(font)
        self.password_login_btn.SetCursor(wx.Cursor(wx.CURSOR_HAND))

        self.sms_login_btn = wx.StaticText(self, -1, "短信登录")
        self.sms_login_btn.SetFont(font)
        self.sms_login_btn.SetCursor(wx.Cursor(wx.CURSOR_HAND))

        swicher_hbox = wx.BoxSizer(wx.HORIZONTAL)
        swicher_hbox.AddStretchSpacer()
        swicher_hbox.Add(self.password_login_btn, 0, wx.ALL, 10)
        swicher_hbox.AddSpacer(20)
        swicher_hbox.Add(self.sms_login_btn, 0, wx.ALL, 10)
        swicher_hbox.AddStretchSpacer()

        note_vbox = wx.BoxSizer(wx.VERTICAL)
        note_vbox.AddStretchSpacer()
        note_vbox.Add(swicher_hbox, 0, wx.EXPAND)
        note_vbox.AddSpacer(10)
        note_vbox.Add(self.note, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        note_vbox.AddStretchSpacer()

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(qrcode_vbox, 0, wx.EXPAND)
        hbox.Add(note_vbox, 0, wx.EXPAND)

        self.SetSizerAndFit(hbox)

    def init_utils(self):
        # 共用一个 session
        self.session = requests.sessions.Session()

        self.login = QRLogin(self.session)
        self.login.init_qrcode()

        # 开启轮询，获取扫码状态
        self.timer = wx.Timer(self, -1)
        self.timer.Start(1000)

    def Bind_EVT(self):
        self.Bind(wx.EVT_CLOSE, self.onClose)

        self.Bind(wx.EVT_TIMER, self.onTimer, self.timer)

        self.password_login_btn.Bind(wx.EVT_LEFT_DOWN, self.onSwitchPasswordLogin)
        self.sms_login_btn.Bind(wx.EVT_LEFT_DOWN, self.onSwitchSMSLogin)

    def onClose(self, event):
        # 关闭窗口，停止轮询并关闭 session
        self.timer.Stop()

        self.session.close()

        event.Skip()

    def onTimer(self, event):
        def _success(info):
            Config.User.login = True
            Config.User.face_url = info["face_url"]
            Config.User.username = info["username"]
            Config.User.sessdata = info["sessdata"]

            kwargs = {
                "login": True,
                "face_url": info["face_url"],
                "username": info["username"],
                "sessdata": info["sessdata"],
                "timestamp": round(time.time())
            }

            utils = ConfigUtils()
            utils.update_config_kwargs(Config.User.user_config_path, "user", **kwargs)

            wx.CallAfter(self.callback)

        def _refresh():
            self.login.init_qrcode()

            self.lab.SetLabel("请使用哔哩哔哩客户端扫码登录")
            self.qrcode.SetBitmap(wx.Image(BytesIO(self.login.get_qrcode())).Scale(250, 250).ConvertToBitmap())

            self.Layout()

        match self.login.check_scan()["code"]:
            case 0:
                info = self.login.get_user_info()
                _success(info)

            case 86090:
                self.lab.SetLabel("请在设备侧确认登录")
                self.Layout()

            case 86038:
                wx.CallAfter(_refresh)
    
    def onSwitchPasswordLogin(self, event):
        def _set_dark_mode():
            if Config.Sys.dark_mode:
                self.sms_login_btn.SetForegroundColour("white")
            else:
                self.sms_login_btn.SetForegroundColour("black")

        _set_dark_mode()

        self.password_login_btn.SetForegroundColour(wx.Colour(79, 165, 217))

        self.note.ChangeSelection(0)

        self.Refresh()

    def onSwitchSMSLogin(self, event):
        def _set_dark_mode():
            if Config.Sys.dark_mode:
                self.password_login_btn.SetForegroundColour("white")
            else:
                self.password_login_btn.SetForegroundColour("black")

        _set_dark_mode()
                
        self.sms_login_btn.SetForegroundColour(wx.Colour(79, 165, 217))

        self.note.ChangeSelection(1)

        self.Refresh()

class LoginPage(wx.Panel):
    def __init__(self, parent, session: requests.sessions.Session):
        self.session = session

        wx.Panel.__init__(self, parent, -1)

        self._init_UI()

        self._init_utils()

    def _init_UI(self):
        def _set_dark_mode():
            if not Config.Sys.dark_mode:
                self.SetBackgroundColour("white")
        
        _set_dark_mode()

    def _init_utils(self):
        self.isLogin = False

    def check_login_result(self, result: Dict):
        if result["code"] != 0:
            wx.MessageDialog(self, f"登录失败\n\n{result['message']} ({result['code']})", "警告", wx.ICON_WARNING).ShowModal()

        else:
            if result["data"]["status"] != 0:
                wx.MessageDialog(self, f"登录失败\n\n{result['data']['message']} ({result['data']['status']})", "警告", wx.ICON_WARNING).ShowModal()

                return

            # 登录成功，关闭窗口
            self.isLogin = True

            user_info = self.login.get_user_info()

            self.GetParent().GetParent().login_success(user_info)

    def get_finger_spi(self):
        # 开启后台线程，获取指纹 spi 等信息
        background_thread = Thread(target = self.login.init_finger)
        background_thread.start()

    def check_captcha(self):
        # 显示极验 captcha 窗口
        captcha_window = CaptchaWindow(self)
        captcha_window.ShowModal()

class PasswordPage(LoginPage):
    def __init__(self, parent, session):
        LoginPage.__init__(self, parent, session)

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

    def init_UI(self):
        def _get_scale_size(_size: tuple):
            match Config.Sys.platform:
                case "windows":
                    return self.FromDIP(_size)
                
                case "linux" | "darwin":
                    return wx.DefaultSize

        username_lab = wx.StaticText(self, -1, "账号")
        self.username_box = wx.TextCtrl(self, -1, size = _get_scale_size((200, 26)))

        username_hbox = wx.BoxSizer(wx.HORIZONTAL)
        username_hbox.Add(username_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        username_hbox.Add(self.username_box, 1, wx.ALL & (~wx.LEFT), 10)

        password_lab = wx.StaticText(self, -1, "密码")
        self.password_box = wx.TextCtrl(self, -1, size = _get_scale_size((200, 26)), style = wx.TE_PASSWORD)

        password_hbox = wx.BoxSizer(wx.HORIZONTAL)
        password_hbox.Add(password_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        password_hbox.Add(self.password_box, 1, wx.ALL & (~wx.LEFT), 10)

        self.login_btn = wx.Button(self, -1, "登录", size = _get_scale_size((120, 30)))

        login_hbox = wx.BoxSizer(wx.HORIZONTAL)
        login_hbox.AddStretchSpacer()
        login_hbox.Add(self.login_btn, 0, wx.ALL, 10)
        login_hbox.AddStretchSpacer()

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(username_hbox, 0, wx.EXPAND)
        vbox.Add(password_hbox, 0, wx.EXPAND)
        vbox.Add(login_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def Bind_EVT(self):
        self.login_btn.Bind(wx.EVT_BUTTON, self.onLogin)

    def init_utils(self):
        self.login = PasswordLogin(self.session)

    def onLogin(self, event):
        if not self.username_box.GetValue():
            wx.MessageDialog(self, "登录失败\n\n账号不能为空", "警告", wx.ICON_WARNING).ShowModal()
            return
        
        if not self.password_box.GetValue():
            wx.MessageDialog(self, "登录失败\n\n密码不能为空", "警告", wx.ICON_WARNING).ShowModal()
            return
        
        self.check_captcha()

        # 获取公钥
        self.login.get_public_key()

        # 将密码进行加盐加密
        password_encrypt = self.login.encrypt_password(self.password_box.GetValue())
        username = self.username_box.GetValue()

        # 进行登录操作
        result = self.login.login(username, password_encrypt)

        self.check_login_result(result)

class SMSPage(LoginPage):
    def __init__(self, parent, session):
        LoginPage.__init__(self, parent, session)

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

    def init_UI(self):
        def _get_scale_size(_size: tuple):
            match Config.Sys.platform:
                case "windows":
                    return self.FromDIP(_size)
                
                case "linux" | "darwin":
                    return wx.DefaultSize

        country_lab = wx.StaticText(self, -1, "区号")
        self.country_choice = wx.Choice(self, -1)

        phone_number_lab = wx.StaticText(self, -1, "手机号")
        self.phone_number_box = wx.TextCtrl(self, -1)
        self.get_validate_code_btn = wx.Button(self, -1, "获取验证码")

        validate_code_lab = wx.StaticText(self, -1, "验证码")
        self.validate_code_box = wx.TextCtrl(self, -1)

        bag_box = wx.GridBagSizer(3, 3)
        bag_box.Add(country_lab, pos = (0, 0), flag = wx.ALL | wx.ALIGN_CENTER, border = 10)
        bag_box.Add(self.country_choice, pos = (0, 1), span = (0, 2), flag = wx.ALL & (~wx.LEFT), border = 10)
        bag_box.Add(phone_number_lab, pos = (1, 0), flag = wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, border = 10)
        bag_box.Add(self.phone_number_box, pos = (1, 1), flag = wx.ALL & (~wx.LEFT) & (~wx.TOP) | wx.ALIGN_CENTER | wx.ALIGN_CENTER, border = 10)
        bag_box.Add(self.get_validate_code_btn, pos = (1, 2), flag = wx.ALL & (~wx.LEFT) & (~wx.TOP), border = 10)
        bag_box.Add(validate_code_lab, pos = (2, 0), flag = wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, border = 10)
        bag_box.Add(self.validate_code_box, pos = (2, 1), span = (2, 2), flag = wx.ALL & (~wx.LEFT) & (~wx.TOP) | wx.EXPAND, border = 10)

        self.login_btn = wx.Button(self, -1, "登录", size = _get_scale_size((120, 30)))

        login_hbox = wx.BoxSizer(wx.HORIZONTAL)
        login_hbox.AddStretchSpacer()
        login_hbox.Add(self.login_btn, 0, wx.ALL, 10)
        login_hbox.AddStretchSpacer()

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(bag_box)
        vbox.Add(login_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def Bind_EVT(self):
        self.get_validate_code_btn.Bind(wx.EVT_BUTTON, self.onGetValidateCode)
        self.login_btn.Bind(wx.EVT_BUTTON, self.onLogin)

    def init_utils(self):
        self.login = SMSLogin(self.session)

        # 获取国际区号列表
        data = self.login.get_country_list()

        self.set_country_list(data)

    def set_country_list(self, data):
        country_data_list = data["data"]["list"]

        self.country_id_list = [entry["country_code"] for entry in country_data_list]
        country_list = [f"+{entry['country_code']} - {entry['cname']}" for entry in country_data_list]

        self.country_choice.Set(country_list)
        self.country_choice.SetSelection(0)

    def onGetValidateCode(self, event):
        if not self.phone_number_box.GetValue():
            wx.MessageDialog(self, "发送验证码失败\n\n手机号不能为空", "警告", wx.ICON_WARNING).ShowModal()
            return
        
        self.check_captcha()

        cid = self.country_id_list[self.country_choice.GetSelection()]
        tel = int(self.phone_number_box.GetValue())

        # 发送短信验证码
        result = self.login.send_sms(tel, cid)

        self.check_sms_send_status(result)

    def check_sms_send_status(self, result):
        # 检查短信是否发送成功
        if result["code"] != 0:
            wx.MessageDialog(self, f"发送验证码失败\n\n{result['message']} ({result['code']})", "警告", wx.ICON_WARNING).ShowModal()

        else:
            # 发送成功，倒计时一分钟
            self.get_validate_code_btn.Enable(False)

            countdown_thread = Thread(target = self.countdown_thread)
            countdown_thread.start()

    def countdown_thread(self):
        for i in range(60, 0, -1):
            if self.isLogin:
                return
            
            wx.CallAfter(self.update_countdown_info, i)
            time.sleep(1)

        wx.CallAfter(self.countdown_finished)

    def countdown_finished(self):
        # 倒计时结束，恢复按钮
        self.get_validate_code_btn.SetLabel("重新发送")
        self.get_validate_code_btn.Enable(True)

    def update_countdown_info(self, seconds: int):
        # 更新倒计时信息
        self.get_validate_code_btn.SetLabel(f"重新发送({seconds})")
    
    def onLogin(self, event):
        if not self.phone_number_box.GetValue():
            wx.MessageDialog(self, "登录失败\n\n手机号不能为空", "警告", wx.ICON_WARNING).ShowModal()
            return
        
        if not self.validate_code_box.GetValue():
            wx.MessageDialog(self, "登录失败\n\n验证码不能为空", "警告", wx.ICON_WARNING).ShowModal()
            return

        tel = int(self.phone_number_box.GetValue())
        code = int(self.validate_code_box.GetValue())
        cid = self.country_id_list[self.country_choice.GetSelection()]

        result = self.login.login(tel, code, cid)

        self.check_login_result(result)