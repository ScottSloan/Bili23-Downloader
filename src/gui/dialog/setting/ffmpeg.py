import wx
import gettext

from utils.config import Config
from utils.common.style.icon_v4 import Icon, IconID

from utils.module.ffmpeg_v2 import FFmpeg

from gui.component.window.dialog import Dialog
from gui.component.button.bitmap_button import BitmapButton

_ = gettext.gettext

class DetectDialog(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent, _("自动检测"))

        self.init_UI()

        self.Bind_EVT()

        self.CenterOnParent()

        self.init_utils()

    def init_UI(self):
        select_lab = wx.StaticText(self, -1, _("请选择 FFmpeg 路径"))

        self.refresh_btn = BitmapButton(self, Icon.get_icon_bitmap(IconID.Refresh))
        self.refresh_btn.SetToolTip(_("刷新"))

        top_hbox = wx.BoxSizer(wx.HORIZONTAL)
        top_hbox.Add(select_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        top_hbox.Add(self.refresh_btn, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))

        self.env_chk = wx.RadioButton(self, -1, _("环境变量"))
        self.env_path_lab = wx.StaticText(self, -1, _("未检测到 FFmpeg"), size = self.FromDIP((450, 20)), style = wx.ST_ELLIPSIZE_MIDDLE)

        self.cwd_chk = wx.RadioButton(self, -1, _("运行目录"))
        self.cwd_path_lab = wx.StaticText(self, -1, _("未检测到 FFmpeg"), size = self.FromDIP((450, 20)), style = wx.ST_ELLIPSIZE_MIDDLE)

        self.ok_btn = wx.Button(self, wx.ID_OK, _("确定"), size = self.get_scaled_size((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, _("取消"), size = self.get_scaled_size((80, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer(1)
        bottom_hbox.Add(self.ok_btn, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        bottom_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(top_hbox, 0, wx.EXPAND)
        vbox.Add(self.env_chk, 0, wx.ALL, self.FromDIP(6))
        vbox.Add(self.env_path_lab, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        vbox.Add(self.cwd_chk, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        vbox.Add(self.cwd_path_lab, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def init_utils(self):
        self.detect_location()

    def Bind_EVT(self):
        self.refresh_btn.Bind(wx.EVT_BUTTON, self.onRefresh)

    def onRefresh(self, event):
        self.detect_location()

    def detect_location(self):
        def set_enable(chk_control: wx.Window, lab_control: wx.Window, path: str):
            enable = bool(path)
        
            chk_control.Enable(enable)
            lab_control.Enable(enable)

            lab = path if enable else _("未检测到 FFmpeg")

            lab_control.SetLabel(lab)
            lab_control.SetToolTip(lab)

        ffmpeg_path = FFmpeg.Env.get_ffmpeg_path()

        env_path, cwd_path = ffmpeg_path["env_path"], ffmpeg_path["cwd_path"]

        set_enable(self.env_chk, self.env_path_lab, env_path)
        set_enable(self.cwd_chk, self.cwd_path_lab, cwd_path)

        if Config.Merge.ffmpeg_path == env_path:
            self.env_chk.SetValue(True)

        if Config.Merge.ffmpeg_path == cwd_path:
            self.cwd_chk.SetValue(True)

        self.ok_btn.Enable(self.env_chk.GetValue() or self.cwd_chk.GetValue())

    def getPath(self):
        if self.env_chk.GetValue():
            return self.env_path_lab.GetLabel()

        if self.cwd_chk.GetValue():
            return self.cwd_path_lab.GetLabel()
