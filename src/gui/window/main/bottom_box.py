import wx
import time

from utils.config import Config
from utils.common.thread import Thread

from utils.module.pic.face import Face

from gui.id import ID

from gui.component.panel.panel import Panel
from gui.component.button.button import Button
from gui.component.menu.user import UserMenu
from gui.component.staticbitmap.staticbitmap import StaticBitmap

class BottomBox(Panel):
    def __init__(self, parent):
        Panel.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

    def init_UI(self):
        self.face_icon = StaticBitmap(self, size = self.FromDIP((32, 32)))
        self.face_icon.SetCursor(wx.Cursor(wx.CURSOR_HAND))
        self.face_icon.Hide()
        self.uname_lab = wx.StaticText(self, -1, "未登录")
        self.uname_lab.SetCursor(wx.Cursor(wx.CURSOR_HAND))
        self.download_mgr_btn = Button(self, "下载管理", size = self.get_scaled_size((100, 30)))
        self.download_btn = Button(self, "开始下载", size = self.get_scaled_size((100, 30)))
        self.download_btn.Enable(False)

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.Add(self.face_icon, 0, wx.ALL & (~wx.RIGHT), self.FromDIP(6))
        bottom_hbox.Add(self.uname_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(self.download_mgr_btn, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        bottom_hbox.Add(self.download_btn, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.SetSizer(bottom_hbox)

    def Bind_EVT(self):
        self.face_icon.Bind(wx.EVT_LEFT_DOWN, self.onShowUserMenuEVT)
        self.uname_lab.Bind(wx.EVT_LEFT_DOWN, self.onShowUserMenuEVT)

    def onShowUserMenuEVT(self, event: wx.MouseEvent):
        if Config.User.login:
            menu = UserMenu()

            self.PopupMenu(menu)
        else:
            evt = wx.PyCommandEvent(wx.EVT_MENU.typeId, id = ID.LOGIN_MENU)
            wx.PostEvent(self.GetEventHandler(), evt)

    def show_user_info(self):
        self.face_icon.Show()
        self.uname_lab.Show()

        image = Face.get_user_face_image()
        
        self.face_icon.SetBitmap(bmp = Face.crop_round_face_bmp(image))
        self.uname_lab.SetLabel(Config.User.username)

        self.GetSizer().Layout()

    def hide_user_info(self):
        self.face_icon.Hide()
        self.uname_lab.Hide()

        self.GetSizer().Layout()

    def set_not_login(self):
        self.face_icon.Hide()
        self.uname_lab.SetLabel("未登录")

        self.GetSizer().Layout()

    def download_tip(self):
        def worker():
            wx.CallAfter(self.download_btn.SetLabel, "✔️已开始下载")
            
            time.sleep(1)

            wx.CallAfter(self.download_btn.SetLabel, "开始下载")

        if not Config.Basic.auto_show_download_window:
            Thread(target = worker).start()