import wx

from utils.tool_v2 import FFmpegCheckTool
from utils.common.icon_v2 import IconManager, IconType
from utils.config import Config

class DetectDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, "自动检测")

        self.init_UI()

        self.Bind_EVT()

        self.CenterOnParent()

        self.init_utils()

    def init_UI(self):
        def _set_dark_mode():
            if not Config.Sys.dark_mode:
                self.SetBackgroundColour("white")
        
        def _get_scale_button_size():
            match Config.Sys.platform:
                case "windows":
                    return self.FromDIP((24, 24))
                
                case "linux" | "darwin":
                    return self.FromDIP((32, 32))
                
        def _get_style():
            match Config.Sys.platform:
                case "windows" | "darwin":
                    return 0
                
                case "linux":
                    return wx.NO_BORDER
        
        _set_dark_mode()

        icon_manager = IconManager(self.GetDPIScaleFactor())

        select_lab = wx.StaticText(self, -1, "请选择 FFmpeg 路径")

        self.refresh_btn = wx.BitmapButton(self, -1, icon_manager.get_icon_bitmap(IconType.REFRESH_ICON), size = _get_scale_button_size(), style = _get_style())
        self.refresh_btn.SetToolTip("刷新")

        top_hbox = wx.BoxSizer(wx.HORIZONTAL)
        top_hbox.Add(select_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        top_hbox.Add(self.refresh_btn, 0, wx.ALL, 10)

        self.env_chk = wx.RadioButton(self, -1, "环境变量")
        self.env_path_lab = wx.StaticText(self, -1, "未检测到 FFmpeg", size = self.FromDIP((350, 20)), style = wx.ST_ELLIPSIZE_END)

        self.cwd_chk = wx.RadioButton(self, -1, "运行目录")
        self.cwd_path_lab = wx.StaticText(self, -1, "未检测到 FFmpeg", size = self.FromDIP((350, 20)), style = wx.ST_ELLIPSIZE_END)

        self.env_chk.Enable(False)
        self.env_path_lab.Enable(False)
        self.cwd_chk.Enable(False)
        self.cwd_path_lab.Enable(False)

        self.ok_btn = wx.Button(self, wx.ID_OK, "确定", size = self.FromDIP((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, "取消", size = self.FromDIP((80, 30)))

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
        cwd_path = FFmpegCheckTool._get_ffmpeg_cwd_path()
        env_path = FFmpegCheckTool._get_ffmpeg_env_path()

        if env_path:
            self.env_chk.Enable(True)
            self.env_path_lab.Enable(True)

            self.env_path_lab.SetLabel(env_path)
            self.env_path_lab.SetToolTip(env_path)
        else:
            self.env_chk.Enable(False)
            self.env_path_lab.Enable(False)

            self.env_path_lab.SetLabel("未检测到 FFmpeg")
            self.env_path_lab.SetToolTip("未检测到 FFmpeg")

        if cwd_path:
            self.cwd_chk.Enable(True)
            self.cwd_path_lab.Enable(True)
            
            self.cwd_path_lab.SetLabel(cwd_path)
            self.cwd_path_lab.SetToolTip(cwd_path)
        else:
            self.cwd_chk.Enable(False)
            self.cwd_path_lab.Enable(False)

            self.cwd_path_lab.SetLabel("未检测到 FFmpeg")
            self.cwd_path_lab.SetToolTip("未检测到 FFmpeg")

        if Config.FFmpeg.path == env_path:
            self.env_chk.SetValue(True)
        else:
            self.cwd_chk.SetValue(True)

    def Bind_EVT(self):
        self.ok_btn.Bind(wx.EVT_BUTTON, self.onConfirm)

        self.refresh_btn.Bind(wx.EVT_BUTTON, self.onRefresh)

    def onRefresh(self, event):
        self.init_utils()

    def onConfirm(self, event):
        if self.env_chk.GetValue() or self.cwd_chk.GetValue():
            event.Skip()
        else:
            wx.MessageDialog(self, "未选择路径\n\n请从下方选择 FFmpeg 路径", "警告", style = wx.ICON_WARNING).ShowModal()

    def getPath(self):
        if self.env_chk.GetValue():
            return self.env_path_lab.GetLabel()

        if self.cwd_chk.GetValue():
            return self.cwd_path_lab.GetLabel()
