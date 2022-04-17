import wx
import os
import time
from threading import Thread

from utils.login import Login
from utils.config import Config

from gui.templates import Dialog

class LoginWindow(Dialog):
    def __init__(self, parent):
        self.parent = parent

        Dialog.__init__(self, parent, "登录", (250, 330))

        self.Center()

        self.login = Login()
        
        self.init_controls()
        self.Bind_EVT()

        wait_t = Thread(target = self.wait_scan)
        wait_t.start()

    def init_controls(self):
        self.panel.SetBackgroundColour("white")

        scan_lab = wx.StaticText(self.panel, -1, "扫描二维码登录")
        scan_lab.SetFont(wx.Font(12, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, faceName = "微软雅黑"))

        qrcode_bitmap = wx.Image("qrcode.png", type = wx.BITMAP_TYPE_PNG).Scale(200, 200)

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
        os.remove("qrcode.png")

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

        self.Hide()

        if status[0]:
            self.set_cookie(status[2]["SESSDATA"])

            wx.MessageDialog(self, "登录成功\n\n扫码登录成功，Cookie 已填入。", "提示", wx.ICON_INFORMATION).ShowModal()
    
    def set_cookie(self, sessdata: str):
        Config.cookie_sessdata = sessdata

        self.parent.sessdata_tc.SetValue(sessdata)

        self.parent.save_conf()