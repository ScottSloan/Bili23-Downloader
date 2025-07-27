import wx

from utils.common.color import Color
from utils.common.pic_v2 import Pic, PicID

from gui.component.text_ctrl.search_ctrl import SearchCtrl

from gui.component.window.dialog import Dialog
from gui.component.panel.panel import Panel

class QRCodePanel(Panel):
    def __init__(self, parent):
        Panel.__init__(self, parent)

        self.init_UI()

    def init_UI(self):
        font: wx.Font = self.GetFont()
        font.SetFractionalPointSize(int(font.GetFractionalPointSize() + 3))

        scan_lab = wx.StaticText(self, -1, "扫描二维码登录")
        scan_lab.SetFont(font)
        scan_lab.SetForegroundColour(Color.get_text_color())

        self.qrcode = wx.StaticBitmap(self, -1, size = self.FromDIP((150, 150)))

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

    def init_utils(self):
        self.set_tip(["正在加载"])

    def set_tip(self, text: list):
        font: wx.Font = self.GetFont()
        font.SetFractionalPointSize(int(font.GetFractionalPointSize() + 5))

        bmp = wx.Bitmap(self.FromDIP(150), self.FromDIP(150))
        dc = wx.MemoryDC(bmp)
        dc.SetFont(font)
        dc.Clear()

        client_height = self.FromDIP(150)
        total_text_height = sum(dc.GetTextExtent(line).height for line in text) + self.FromDIP(4) * (len(text) - 1)
        y_start = (client_height - total_text_height) // 2

        for line in text:
            text_width, text_height = dc.GetTextExtent(line)
            x = (self.FromDIP(150) - text_width) // 2
            dc.DrawText(line, x, y_start)
            y_start += text_height + self.FromDIP(4)

        dc.SetPen(wx.Pen(Color.get_border_color(), width = 1))
        dc.SetBrush(wx.TRANSPARENT_BRUSH)

        dc.DrawRectangle(2, 2, bmp.GetWidth() - 4, bmp.GetHeight() - 4)

        self.qrcode.SetBitmap(bmp)

class SMSPanel(Panel):
    def __init__(self, parent):
        Panel.__init__(self, parent)

        self.init_UI()

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
    
    def init_utils(self):
        pass

class LoginDialog(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent, "登录")

        self.init_UI()

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

        self.left_bmp = wx.StaticBitmap(self, -1, Pic.get_pic_bitmap(PicID.Left_Onnanoko))
        self.right_bmp = wx.StaticBitmap(self, -1, Pic.get_pic_bitmap(PicID.Right_Onnanoko))

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
        self.qrcode_panel.init_utils()
        self.sms_panel.init_utils()