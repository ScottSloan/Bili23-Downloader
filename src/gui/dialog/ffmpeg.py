import wx

from utils.module.ffmpeg import FFmpeg
from utils.config import Config
from utils.common.icon_v2 import IconManager, IconType

from gui.component.dialog import Dialog
from gui.component.bitmap_button import BitmapButton

class DetectDialog(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent, "自动检测")

        self.init_UI()

        self.Bind_EVT()

        self.CenterOnParent()

        self.init_utils()

    def init_UI(self):
        self.set_dark_mode()

        icon_manager = IconManager(self)

        select_lab = wx.StaticText(self, -1, "请选择 FFmpeg 路径")

        self.refresh_btn = BitmapButton(self, -1, icon_manager.get_icon_bitmap(IconType.REFRESH_ICON), size = self.get_scaled_size((24, 24)))
        self.refresh_btn.SetToolTip("刷新")

        top_hbox = wx.BoxSizer(wx.HORIZONTAL)
        top_hbox.Add(select_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        top_hbox.Add(self.refresh_btn, 0, wx.ALL | wx.ALIGN_CENTER, 10)

        self.env_chk = wx.RadioButton(self, -1, "环境变量")
        self.env_path_lab = wx.StaticText(self, -1, "未检测到 FFmpeg", size = self.FromDIP((350, 20)), style = wx.ST_ELLIPSIZE_END)

        self.cwd_chk = wx.RadioButton(self, -1, "运行目录")
        self.cwd_path_lab = wx.StaticText(self, -1, "未检测到 FFmpeg", size = self.FromDIP((350, 20)), style = wx.ST_ELLIPSIZE_END)

        self.ok_btn = wx.Button(self, wx.ID_OK, "确定", size = self.get_scaled_size((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, "取消", size = self.get_scaled_size((80, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer(1)
        bottom_hbox.Add(self.ok_btn, 0, wx.ALL & (~wx.TOP), 10)
        bottom_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), 10)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(top_hbox, 0, wx.EXPAND)
        vbox.Add(self.env_chk, 0, wx.ALL, 10)
        vbox.Add(self.env_path_lab, 0, wx.ALL & (~wx.TOP), 10)
        vbox.Add(self.cwd_chk, 0, wx.ALL & (~wx.TOP), 10)
        vbox.Add(self.cwd_path_lab, 0, wx.ALL & (~wx.TOP), 10)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.AddSpacer(30)
        hbox.Add(vbox, 0, wx.EXPAND)
        hbox.AddSpacer(30)

        dlg_vbox = wx.BoxSizer(wx.VERTICAL)
        dlg_vbox.Add(hbox, 0, wx.EXPAND)
        dlg_vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(dlg_vbox)

    def init_utils(self):
        self.ffmpeg = FFmpeg()

        self.detect_location()

    def Bind_EVT(self):
        self.ok_btn.Bind(wx.EVT_BUTTON, self.onConfirm)

        self.refresh_btn.Bind(wx.EVT_BUTTON, self.onRefresh)

    def onRefresh(self, event):
        self.detect_location()

    def onConfirm(self, event):
        if self.env_chk.GetValue() or self.cwd_chk.GetValue():
            event.Skip()
        else:
            wx.MessageDialog(self, "未选择路径\n\n请从下方选择 FFmpeg 路径", "警告", style = wx.ICON_WARNING).ShowModal()

    def detect_location(self):
        def set_env_enable(path: str):
            self.env_chk.Enable(bool(path))
            self.env_path_lab.Enable(bool(path))

            self.env_path_lab.SetLabel(path if path else "未检测到 FFmpeg")
            self.env_path_lab.SetToolTip(path if path else "未检测到 FFmpeg")

        def set_cwd_enable(path: str):
            self.cwd_chk.Enable(bool(path))
            self.cwd_path_lab.Enable(bool(path))

            self.cwd_path_lab.SetLabel(path if path else "未检测到 FFmpeg")
            self.cwd_path_lab.SetToolTip(path if path else "未检测到 FFmpeg")

        cwd_path = self.ffmpeg.get_cwd_path()
        env_path = self.ffmpeg.get_env_path()

        set_cwd_enable(cwd_path)
        set_env_enable(env_path)

        if Config.FFmpeg.path == env_path:
            self.env_chk.SetValue(True)
        else:
            self.cwd_chk.SetValue(True)

    def getPath(self):
        if self.env_chk.GetValue():
            return self.env_path_lab.GetLabel()

        if self.cwd_chk.GetValue():
            return self.cwd_path_lab.GetLabel()
