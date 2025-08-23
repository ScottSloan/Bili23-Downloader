import wx
import time

from utils.common.style.color import Color
from utils.common.style.pic_v2 import Pic, PicID
from utils.common.thread import Thread
from utils.common.enums import QRCodeStatus
from utils.common.exception import show_error_message_dialog

from utils.auth.login_v2 import Login, LoginInfo
from utils.module.web.page import WebPage

from gui.component.text_ctrl.search_ctrl import SearchCtrl
from gui.component.staticbitmap.staticbitmap import StaticBitmap

from gui.component.window.dialog import Dialog
from gui.component.panel.panel import Panel

class QRCodePanel(Panel):
    def __init__(self, parent):
        self.parent: LoginDialog = parent

        Panel.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

    def init_UI(self):
        font: wx.Font = self.GetFont()
        font.SetFractionalPointSize(int(font.GetFractionalPointSize() + 3))

        scan_lab = wx.StaticText(self, -1, "扫描二维码登录")
        scan_lab.SetFont(font)
        scan_lab.SetForegroundColour(Color.get_text_color())

        self.qrcode = StaticBitmap(self, size = self.FromDIP((150, 150)))

        qrcode_hbox = wx.BoxSizer(wx.HORIZONTAL)
        qrcode_hbox.AddStretchSpacer()
        qrcode_hbox.Add(self.qrcode, 0, wx.EXPAND)
        qrcode_hbox.AddStretchSpacer()

        font: wx.Font = self.GetFont()
        font.SetFractionalPointSize(int(font.GetFractionalPointSize() + 1))

        self.scan_tip_lab = wx.StaticText(self, -1, "请使用哔哩哔哩客户端扫码登录")
        self.scan_tip_lab.SetFont(font)
        self.scan_tip_lab.SetForegroundColour(Color.get_text_color())

        qrcode_vbox = wx.BoxSizer(wx.VERTICAL)
        qrcode_vbox.Add(scan_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        qrcode_vbox.Add(qrcode_hbox, 0, wx.EXPAND)
        qrcode_vbox.Add(self.scan_tip_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))

        self.timer = wx.Timer(self, -1)

        self.SetSizer(qrcode_vbox)

    def Bind_EVT(self):
        self.qrcode.Bind(wx.EVT_LEFT_DOWN, self.onRefreshEVT)

        self.Bind(wx.EVT_TIMER, self.onTimerEVT)

    def init_utils(self):
        wx.CallAfter(self.qrcode.SetTextTip, ["正在加载"])
        
        self.show_qrcode()

        wx.CallAfter(self.timer.Start, 1000)

    def show_qrcode(self):
        def worker():
            self.qrcode.SetBitmap(image = wx.Image(img_io))
            self.qrcode.SetSize(self.FromDIP((149, 149)))

        Login.QRCode.generate_qrcode()

        img_io = Login.QRCode.get_qrcode_img_io()

        wx.CallAfter(worker)

    def onTimerEVT(self, event):
        resp = Login.QRCode.check_scan_status()

        match QRCodeStatus(resp.get("code")):
            case QRCodeStatus.Success:
                self.status_success()

            case QRCodeStatus.Confirm:
                self.status_confirm()

            case QRCodeStatus.Outdated:
                self.status_outdated()

    def onRefreshEVT(self, event):
        Thread(target = self.init_utils).start()

    def status_success(self):
        self.timer.Stop()

        wx.CallAfter(self.qrcode.SetTextTip, ["登录成功"])

        info = Login.get_user_info(login = True)
        Login.login(info)

        self.parent.onSuccess()

    def status_confirm(self):
        self.scan_tip_lab.SetLabel("请在设备侧确认登录")
        self.Layout()

    def status_outdated(self):
        def worker():
            self.qrcode.SetTextTip(["二维码已过期", "点击重新加载"])

            self.qrcode.SetCursor(wx.Cursor(wx.CURSOR_HAND))

        self.timer.Stop()

        wx.CallAfter(worker)

class SMSPanel(Panel):
    def __init__(self, parent):
        self.parent: LoginDialog = parent

        Panel.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

    def init_UI(self):
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

        sms_vbox = wx.BoxSizer(wx.VERTICAL)
        sms_vbox.AddStretchSpacer()
        sms_vbox.Add(swicher_hbox, 0, wx.EXPAND)
        sms_vbox.AddSpacer(self.FromDIP(6))
        sms_vbox.Add(flex_sizer, 0, wx.EXPAND)
        sms_vbox.Add(login_hbox, 0, wx.EXPAND)
        sms_vbox.AddStretchSpacer()

        self.SetSizerAndFit(sms_vbox)

        self.timer = wx.Timer(self, -1)
    
    def Bind_EVT(self):
        self.get_validate_code_btn.Bind(wx.EVT_BUTTON, self.onGetValidateCodeEVT)
        self.login_btn.Bind(wx.EVT_BUTTON, self.onLoginEVT)

        self.validate_code_box.Bind(wx.EVT_SET_FOCUS, self.onSetFocusEVT)
        self.validate_code_box.Bind(wx.EVT_KILL_FOCUS, self.onKillFocusEVT)

        self.Bind(wx.EVT_TIMER, self.onTimerEVT)

    def init_utils(self):
        self.countdown = 60

        country_data = Login.SMS.get_country_list()

        wx.CallAfter(self.set_country_list, country_data)

    def onGetValidateCodeEVT(self, event):
        def worker():
            self.check_captcha_status()

            Login.SMS.send_sms(self.tel, self.cid)

            wx.CallAfter(self.start_countdown)
    
        if not self.phone_number_box.GetValue():
            wx.MessageDialog(self.parent, "发送验证码失败\n\n手机号不能为空", "警告", wx.ICON_WARNING).ShowModal()
            return
        
        Thread(target = worker).start()

    def onTimerEVT(self, event):
        def update():
            self.get_validate_code_btn.SetLabel(f"重新发送({self.countdown})")

        def reset():
            self.timer.Stop()
            self.countdown = 60

            self.get_validate_code_btn.SetLabel("重新发送")
            self.get_validate_code_btn.Enable(True)

        self.countdown -= 1
        wx.CallAfter(update)

        if self.countdown == 0:
            wx.CallAfter(reset)

    def onLoginEVT(self, event):
        def worker():
            Login.SMS.login(self.tel, self.cid, int(self.validate_code_box.GetValue()))

            info = Login.get_user_info(login = True)
            Login.login(info)

            self.parent.onSuccess()

        if not self.validate_code_box.GetValue():
            wx.MessageDialog(self.parent, "登录失败\n\n验证码不能为空", "警告", wx.ICON_WARNING).ShowModal()
            return

        Thread(target = worker).start()

    def onSetFocusEVT(self, event: wx.FocusEvent):
        self.parent.set_2233_mask()
        
        event.Skip()

    def onKillFocusEVT(self, event: wx.FocusEvent):
        self.parent.set_2233_normal()
        
        event.Skip()

    def check_captcha_status(self):
        if not LoginInfo.Captcha.seccode:
            Login.Captcha.get_geetest_challenge_gt()

            WebPage.show_webpage(self.parent, "captcha.html")

            while LoginInfo.Captcha.flag:
                time.sleep(1)

    def start_countdown(self):
        self.parent.raise_top()

        self.get_validate_code_btn.SetLabel("重新发送(60)")
        self.get_validate_code_btn.Enable(False)

        self.timer.Start(1000)

    def set_country_list(self, country_desc_list: list):
        self.country_id_list = [entry["country_code"] for entry in country_desc_list]

        country_desc_list = [f"+{entry['country_code']} - {entry['cname']}" for entry in country_desc_list]

        self.country_id_choice.Set(country_desc_list)
        self.country_id_choice.SetSelection(0)

        self.Layout()

    @property
    def cid(self):
        return self.country_id_list[self.country_id_choice.GetSelection()]
    
    @property
    def tel(self):
        return int(self.phone_number_box.GetValue())

class LoginDialog(Dialog):
    def __init__(self, parent):
        from gui.window.main.main_v3 import MainWindow

        self.parent: MainWindow = parent

        Dialog.__init__(self, parent, "登录")

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

        self.CenterOnParent()

    def init_UI(self):
        self.set_dark_mode()

        self.qrcode_panel = QRCodePanel(self)

        split_line = wx.StaticLine(self, -1, style = wx.LI_VERTICAL)

        self.sms_panel = SMSPanel(self)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.AddSpacer(self.FromDIP(60))
        hbox.Add(self.qrcode_panel, 0, wx.EXPAND)
        hbox.AddSpacer(self.FromDIP(30))
        hbox.Add(split_line, 0, wx.EXPAND)
        hbox.AddSpacer(self.FromDIP(30))
        hbox.Add(self.sms_panel, 0, wx.EXPAND)
        hbox.AddSpacer(self.FromDIP(60))

        self.left_bmp = StaticBitmap(self, size = self.FromDIP((104, 95)))
        self.right_bmp = StaticBitmap(self, size = self.FromDIP((97, 95)))
        self.set_2233_normal()

        info_lab = wx.StaticText(self, -1, "重要提示：请先在 B 站网页端完成一次登录操作，再继续使用本程序")
        info_lab.SetFont(self.GetFont().MakeBold())

        info_vbox = wx.BoxSizer(wx.VERTICAL)
        info_vbox.AddStretchSpacer()
        info_vbox.Add(info_lab, 0, wx.ALL, self.FromDIP(6))
        info_vbox.AddStretchSpacer()

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.Add(self.left_bmp, 0, wx.EXPAND)
        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(info_vbox, 0, wx.EXPAND)
        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(self.right_bmp, 0, wx.EXPAND)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.AddSpacer(self.FromDIP(16))
        vbox.Add(hbox, 0, wx.EXPAND)
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def Bind_EVT(self):
        pass

    def init_utils(self):
        def worker():
            self.qrcode_panel.init_utils()
            self.sms_panel.init_utils()
        
        Login.set_on_error_callback(self.onError)

        Thread(target = worker).start()

    def onSuccess(self):
        def worker():
            self.parent.init_menubar()

            self.parent.utils.show_user_info()

            wx.MessageDialog(self.parent, "登录成功\n\n账号登录成功，建议重启程序刷新登录信息。", "提示", wx.ICON_INFORMATION).ShowModal()

        wx.CallAfter(worker)

        event = wx.PyCommandEvent(wx.EVT_CLOSE.typeId, self.GetId())
        wx.PostEvent(self.GetEventHandler(), event)

    def onError(self):
        def worker():
            self.raise_top()

            show_error_message_dialog("登录失败", parent = self)

        wx.CallAfter(worker)

    def set_2233_normal(self):
        self.left_bmp.SetBitmap(image = Pic.get_pic_bitmap(PicID.Left_22))
        self.right_bmp.SetBitmap(image = Pic.get_pic_bitmap(PicID.Right_33))

    def set_2233_mask(self):
        self.left_bmp.SetBitmap(image = Pic.get_pic_bitmap(PicID.Left_22_Mask))
        self.right_bmp.SetBitmap(image = Pic.get_pic_bitmap(PicID.Right_33_Mask))