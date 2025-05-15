import wx
import time
from io import BytesIO
from typing import Dict, Callable
from datetime import datetime, timedelta

from utils.auth.login import QRLogin, SMSLogin
from utils.config import Config, user_config_group
from utils.auth.cookie import CookieUtils

from utils.common.thread import Thread
from utils.common.pic import Pic, PicID
from utils.common.enums import Platform

from gui.component.dialog import Dialog
from gui.component.panel import Panel
from gui.component.search_ctrl import SearchCtrl

class LoginWindow(Dialog):
    def __init__(self, parent, callback: Callable):
        self.callback = callback

        Dialog.__init__(self, parent, "登录")
        
        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

        self.CenterOnParent()

    def init_UI(self):
        self.set_dark_mode()

        self.qr_page = QRPage(self)
        self.sms_page = SMSPage(self)

        line = wx.StaticLine(self, -1, style = wx.LI_VERTICAL)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.AddSpacer(self.FromDIP(60))
        hbox.Add(self.qr_page, 0, wx.EXPAND)
        hbox.AddSpacer(self.FromDIP(30))
        hbox.Add(line, 0, wx.EXPAND)
        hbox.AddSpacer(self.FromDIP(30))
        hbox.Add(self.sms_page, 0, wx.EXPAND)
        hbox.AddSpacer(self.FromDIP(70))

        self.left_bmp = wx.StaticBitmap(self, -1, Pic.get_pic_bitmap(PicID.LeftGirl))
        self.right_bmp = wx.StaticBitmap(self, -1, Pic.get_pic_bitmap(PicID.RightGirl))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.Add(self.left_bmp, 0, wx.EXPAND)
        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(self.right_bmp, 0, wx.EXPAND)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.AddSpacer(self.FromDIP(16))
        vbox.Add(hbox, 0, wx.EXPAND)
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def init_utils(self):
        def worker():
            cookie_utils = CookieUtils()
            cookie_utils.exclimbwuzhi(Config.Auth.buvid3)

        Thread(target = worker).start()

    def Bind_EVT(self):        
        self.Bind(wx.EVT_CLOSE, self.onCloseEVT)

        self.sms_page.validate_code_box.Bind(wx.EVT_SET_FOCUS, self.onValidateBoxSetFocusEVT)
        self.sms_page.validate_code_box.Bind(wx.EVT_KILL_FOCUS, self.onValidateBoxKillFocusEVT)

    def onCloseEVT(self, event):
        self.qr_page.onClose()
        self.sms_page.onClose()

        event.Skip()

    def onValidateBoxSetFocusEVT(self, event):
        self.left_bmp.SetBitmap(Pic.get_pic_bitmap(PicID.LeftGirlMask))
        self.right_bmp.SetBitmap(Pic.get_pic_bitmap(PicID.RightGirlMask))

        event.Skip()

    def onValidateBoxKillFocusEVT(self, event):
        self.left_bmp.SetBitmap(Pic.get_pic_bitmap(PicID.LeftGirl))
        self.right_bmp.SetBitmap(Pic.get_pic_bitmap(PicID.RightGirl))

        event.Skip()

    def onLoginSuccess(self):
        wx.CallAfter(self.callback)
        
        self.Close()

class LoginPage(Panel):
    def __init__(self, parent):
        self.parent = parent

        Panel.__init__(self, parent)

    def getLabelColor(self):
        if Config.Sys.dark_mode:
            return wx.Colour("white")
        else:
            return wx.Colour(80, 80, 80)
    
    def getBorderColor(self):
        if Config.Sys.dark_mode:
            return wx.Colour("white")
        else:
            return wx.Colour(227, 229, 231)

    def onLoginSuccess(self):
        self.GetParent().onLoginSuccess()

class QRPage(LoginPage):
    def __init__(self, parent):
        LoginPage.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

    def init_UI(self):
        font: wx.Font = self.GetFont()
        font.SetFractionalPointSize(int(font.GetFractionalPointSize() + 3))

        font_color = self.getLabelColor()

        scan_lab = wx.StaticText(self, -1, "扫描二维码登录")
        scan_lab.SetFont(font)
        scan_lab.SetForegroundColour(font_color)

        self.qrcode = wx.StaticBitmap(self, -1, self.setQRCodeTextTip("正在加载"), size = self.FromDIP((150, 150)))

        qrcode_hbox = wx.BoxSizer(wx.HORIZONTAL)
        qrcode_hbox.AddStretchSpacer()
        qrcode_hbox.Add(self.qrcode, 0, wx.EXPAND)
        qrcode_hbox.AddStretchSpacer()

        font: wx.Font = self.GetFont()
        font.SetFractionalPointSize(int(font.GetFractionalPointSize() + 1))

        self.scan_tip_lab = wx.StaticText(self, -1, "请使用哔哩哔哩客户端扫码登录")
        self.scan_tip_lab.SetFont(font)
        self.scan_tip_lab.SetForegroundColour(font_color)

        qrcode_vbox = wx.BoxSizer(wx.VERTICAL)
        qrcode_vbox.Add(scan_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        qrcode_vbox.Add(qrcode_hbox, 0, wx.EXPAND)
        qrcode_vbox.Add(self.scan_tip_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))

        self.timer = wx.Timer(self, -1)

        self.SetSizer(qrcode_vbox)
    
    def init_utils(self):
        self.login = QRLogin()
        self.login.init_session()

        self.loadNewQRCode()
        
        self.timer.Start(1000)

    def Bind_EVT(self):
        self.Bind(wx.EVT_TIMER, self.onTimer, self.timer)

        self.qrcode.Bind(wx.EVT_LEFT_DOWN, self.onRefreshQRCode)

    def onTimer(self, event):
        def success():
            self.qrcode.SetBitmap(self.setQRCodeTextTip("登录成功"))
            
            time.sleep(1)

            self.onLoginSuccess()

        def outdated():
            self.qrcode.SetBitmap(self.setQRCodeTextTip("二维码已过期"))
            self.qrcode.SetCursor(wx.Cursor(wx.CURSOR_HAND))

        match self.login.check_scan()["code"]:
            case 0:
                info = self.login.get_user_info()
                self.login.login(info)

                success()

            case 86090:
                self.scan_tip_lab.SetLabel("请在设备侧确认登录")
                self.Layout()

            case 86038:
                self.timer.Stop()
                wx.CallAfter(outdated)
    
    def onRefreshQRCode(self, event):
        self.timer.Start()

        self.scan_tip_lab.SetLabel("请使用哔哩哔哩客户端扫码登录")

        self.qrcode.SetBitmap(self.setQRCodeTextTip("正在加载"))
        self.qrcode.SetCursor(wx.Cursor(wx.CURSOR_ARROW))

        self.loadNewQRCode()

    def onClose(self):
        self.timer.Stop()

        self.login.session.close()

    def setQRCodeTextTip(self, text: str):
        font: wx.Font = self.GetFont()
        font.SetFractionalPointSize(int(font.GetFractionalPointSize() + 5))

        bmp = wx.Bitmap(self.FromDIP(150), self.FromDIP(150))
        dc = wx.MemoryDC(bmp)
        dc.SetTextForeground(self.getLabelColor())
        dc.SetFont(font)

        width, height = dc.GetTextExtent(text)

        x = (self.FromDIP(150) - width) // 2
        y = (self.FromDIP(150) - height) // 2

        dc.Clear()
        dc.DrawText(text, x, y)

        dc.SetPen(wx.Pen(self.getBorderColor(), width = 1))
        dc.SetBrush(wx.TRANSPARENT_BRUSH)

        dc.DrawRectangle(2, 2, bmp.GetWidth() - 4, bmp.GetHeight() - 4)

        return bmp

    def loadNewQRCode(self):
        def worker():
            def set_bmp():
                match Platform(Config.Sys.platform):
                    case Platform.Windows:
                        if self.GetDPIScaleFactor() <= 1.5:
                            scale_size = self.FromDIP((150, 150))
                        else:
                            scale_size = self.FromDIP((75, 75))

                    case Platform.Linux | Platform.macOS:
                        scale_size = self.FromDIP((150, 150))

                qrcode: wx.Image = wx.Image(img).Scale(scale_size[0], scale_size[1], wx.IMAGE_QUALITY_HIGH)

                self.qrcode.SetBitmap(qrcode.ConvertToBitmap())

            self.login.init_qrcode()

            img = BytesIO(self.login.get_qrcode())

            wx.CallAfter(set_bmp)
        
        Thread(target = worker).start()

class SMSPage(LoginPage):
    def __init__(self, parent):
        LoginPage.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

    def init_UI(self):
        self.set_dark_mode()

        font: wx.Font = self.GetFont()
        font.SetFractionalPointSize(int(font.GetFractionalPointSize() + 3))

        self.sms_login_btn = wx.StaticText(self, -1, "短信登录")
        self.sms_login_btn.SetFont(font)
        self.sms_login_btn.SetCursor(wx.Cursor(wx.CURSOR_HAND))
        self.sms_login_btn.SetForegroundColour(wx.Colour(79, 165, 217))

        swicher_hbox = wx.BoxSizer(wx.HORIZONTAL)
        swicher_hbox.AddStretchSpacer()
        swicher_hbox.Add(self.sms_login_btn, 0, wx.ALL, self.FromDIP(6))
        swicher_hbox.AddStretchSpacer()

        country_lab = wx.StaticText(self, -1, "区号")
        self.country_id_choice = wx.Choice(self, -1)

        phone_number_lab = wx.StaticText(self, -1, "手机号")
        self.phone_number_box = SearchCtrl(self, "请输入手机号", size = self.FromDIP((150, 16)))
        self.get_validate_code_btn = wx.Button(self, -1, "获取验证码")

        phone_hbox = wx.BoxSizer(wx.HORIZONTAL)
        phone_hbox.Add(self.phone_number_box, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.EXPAND, self.FromDIP(6))
        phone_hbox.Add(self.get_validate_code_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        validate_code_lab = wx.StaticText(self, -1, "验证码")
        self.validate_code_box = SearchCtrl(self, "请输入验证码")

        flex_sizer = wx.FlexGridSizer(3, 2, 0, 0)

        flex_sizer.Add(country_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        flex_sizer.Add(self.country_id_choice, 0,wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        flex_sizer.Add(phone_number_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
        flex_sizer.Add(phone_hbox, 0, wx.EXPAND)
        flex_sizer.Add(validate_code_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
        flex_sizer.Add(self.validate_code_box, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.EXPAND, self.FromDIP(6))

        self.login_btn = wx.Button(self, -1, "登录", size = self.get_scaled_size((120, 30)))

        login_hbox = wx.BoxSizer(wx.HORIZONTAL)
        login_hbox.AddStretchSpacer()
        login_hbox.Add(self.login_btn, 0, wx.ALL, self.FromDIP(6))
        login_hbox.AddStretchSpacer()

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(swicher_hbox, 0, wx.EXPAND)
        vbox.AddSpacer(self.FromDIP(6))
        vbox.Add(flex_sizer, 0, wx.EXPAND)
        vbox.Add(login_hbox, 0, wx.EXPAND)

        page_vbox = wx.BoxSizer(wx.VERTICAL)
        page_vbox.AddStretchSpacer()
        page_vbox.Add(vbox, 0, wx.EXPAND)
        page_vbox.AddStretchSpacer()

        self.SetSizerAndFit(page_vbox)

        self.timer = wx.Timer(self, -1)

    def Bind_EVT(self):
        self.get_validate_code_btn.Bind(wx.EVT_BUTTON, self.onGetValidateCode)
        self.login_btn.Bind(wx.EVT_BUTTON, self.onLogin)

        self.Bind(wx.EVT_TIMER, self.onTimerEVT)

    def init_utils(self):
        self.count = 60

        self.login = SMSLogin()
        self.login.init_session()

        data = self.login.get_country_list()

        self.set_country_list(data)

    def set_country_list(self, data):
        country_data_list = data["data"]["list"]

        self.country_id_list = [entry["country_code"] for entry in country_data_list]
        country_list = [f"+{entry['country_code']} - {entry['cname']}" for entry in country_data_list]

        self.country_id_choice.Set(country_list)
        self.country_id_choice.SetSelection(0)

    def onGetValidateCode(self, event):
        if not self.phone_number_box.GetValue():
            wx.MessageDialog(self, "发送验证码失败\n\n手机号不能为空", "警告", wx.ICON_WARNING).ShowModal()
            return
        
        self.check_captcha()

        cid = self.country_id_list[self.country_id_choice.GetSelection()]
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

            self.timer.Start(1000)

    def onTimerEVT(self, event):
        def update():
            self.get_validate_code_btn.SetLabel(f"重新发送({self.count})")

        def reset():
            self.timer.Stop()
            self.count = 60

            self.get_validate_code_btn.SetLabel("重新发送")
            self.get_validate_code_btn.Enable(True)

        self.count -= 1
        wx.CallAfter(update)

        if self.count == 0:
            wx.CallAfter(reset)

    def onLogin(self, event):
        if not self.phone_number_box.GetValue():
            wx.MessageDialog(self, "登录失败\n\n手机号不能为空", "警告", wx.ICON_WARNING).ShowModal()
            return
        
        if not self.validate_code_box.GetValue():
            wx.MessageDialog(self, "登录失败\n\n验证码不能为空", "警告", wx.ICON_WARNING).ShowModal()
            return

        tel = int(self.phone_number_box.GetValue())
        code = int(self.validate_code_box.GetValue())
        cid = self.country_id_list[self.country_id_choice.GetSelection()]

        result = self.login.login(tel, code, cid)

        self.check_login_result(result)

    def onClose(self):
        self.login.session.close()

    def check_captcha(self):
        from gui.dialog.captcha import CaptchaWindow

        # 显示极验 captcha 窗口
        captcha_window = CaptchaWindow(self.parent)
        captcha_window.ShowModal()

    def check_login_result(self, result: Dict):
        if result["code"] != 0:
            wx.MessageDialog(self, f"登录失败\n\n{result['message']} ({result['code']})", "警告", wx.ICON_WARNING).ShowModal()
            return
        
        elif result["data"]["status"] != 0:
            wx.MessageDialog(self, f"登录失败\n\n{result['data']['message']} ({result['data']['status']})", "警告", wx.ICON_WARNING).ShowModal()
            return

        self.timer.Stop()

        info = self.login.get_user_info()
        self.login.login(info)

        self.onLoginSuccess()