import wx
from io import BytesIO

from utils.login import QRLogin
from utils.config import Config, conf

class LoginWindow(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, "扫码登录")
        
        self.init_login()

        self.init_UI()

        self.Bind_EVT()

        self.CenterOnParent()

    def init_login(self):
        self.login = QRLogin()
        self.login.init_qrcode()

        self.timer = wx.Timer(self, -1)
        self.timer.Start(1000)

    def init_UI(self):
        self.SetBackgroundColour("white")

        font: wx.Font = self.GetFont()

        scan_lab = wx.StaticText(self, -1, "扫描二维码登录")
        font.SetPointSize(12)
        scan_lab.SetFont(font)

        self.qrcode = wx.StaticBitmap(self, -1, wx.Image(BytesIO(self.login.get_qrcode())).Scale(250, 250).ConvertToBitmap())

        self.lab = wx.StaticText(self, -1, "请使用哔哩哔哩客户端扫码登录")
        font.SetPointSize(10)
        self.lab.SetFont(font)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(scan_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        vbox.Add(self.qrcode, 0, wx.EXPAND)
        vbox.Add(self.lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)

        self.SetSizerAndFit(vbox)
        
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
                self.save_user_info(user_info)

                self.Hide()
                
                wx.CallAfter(self.init_userinfo)

            case 86090:
                self.lab.SetLabel("请在设备侧确认登录")
                self.Layout()

            case 86038:
                wx.CallAfter(self.refresh_qrcode)
    
    def init_userinfo(self):
        self.timer.Stop()
        
        self.GetParent().init_user_info()
        self.GetParent().infobar.ShowMessage("提示：登录成功", flags = wx.ICON_INFORMATION)

    def refresh_qrcode(self):
        self.login = QRLogin()
        self.login.init_qrcode()

        self.lab.SetLabel("请使用哔哩哔哩客户端扫码登录")
        self.qrcode.SetBitmap(wx.Image(BytesIO(self.login.get_qrcode())).Scale(250, 250).ConvertToBitmap())

        self.Layout()

    def save_user_info(self, user_info: dict):
        Config.User.login = True

        Config.User.face = user_info["face"]
        Config.User.uname = user_info["uname"]
        Config.User.sessdata = user_info["sessdata"]

        conf.save_all_user_config()