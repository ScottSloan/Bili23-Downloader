import wx
import os

from utils.config import Config
from utils.common.map import override_option_map
from utils.common.enums import Platform

from gui.window.settings.page import Page
from gui.dialog.setting.ffmpeg import DetectDialog
from gui.component.misc.tooltip import ToolTip

class FFmpegPage(Page):
    def __init__(self, parent: wx.Window):
        Page.__init__(self, parent, "FFmpeg")

        self.init_UI()

        self.Bind_EVT()

        self.load_data()

    def init_UI(self):
        ffmpeg_box = wx.StaticBox(self.panel, -1, "FFmpeg 设置")

        ffmpeg_path_label = wx.StaticText(ffmpeg_box, -1, "FFmpeg 路径")
        self.path_box = wx.TextCtrl(ffmpeg_box, -1)
        self.browse_btn = wx.Button(ffmpeg_box, -1, "浏览", size = self.get_scaled_size((60, 24)))

        path_hbox = wx.BoxSizer(wx.HORIZONTAL)
        path_hbox.Add(self.path_box, 1, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
        path_hbox.Add(self.browse_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.detect_btn = wx.Button(ffmpeg_box, -1, "自动检测", size = self.get_scaled_size((90, 28)))
        self.tutorial_btn = wx.Button(ffmpeg_box, -1, "安装教程", size = self.get_scaled_size((90, 28)))

        self.check_ffmpeg_chk = wx.CheckBox(ffmpeg_box, -1, "启动时自动检查 FFmpeg 可用性")

        btn_hbox = wx.BoxSizer(wx.HORIZONTAL)
        btn_hbox.Add(self.detect_btn, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        btn_hbox.Add(self.tutorial_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))

        ffmpeg_sbox = wx.StaticBoxSizer(ffmpeg_box, wx.VERTICAL)
        ffmpeg_sbox.Add(ffmpeg_path_label, 0, wx.ALL, self.FromDIP(6))
        ffmpeg_sbox.Add(path_hbox, 0, wx.EXPAND)
        ffmpeg_sbox.Add(self.check_ffmpeg_chk, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        ffmpeg_sbox.Add(btn_hbox, 0, wx.EXPAND)

        merge_option_box = wx.StaticBox(self.panel, -1, "音视频合并选项")

        self.keep_original_files_chk = wx.CheckBox(merge_option_box, -1, "合并完成后保留原始文件")
        keep_original_files_tip = ToolTip(merge_option_box)
        keep_original_files_tip.set_tooltip("合并完成后，保留原始的视频和音频文件")

        keep_original_files_hbox = wx.BoxSizer(wx.HORIZONTAL)
        keep_original_files_hbox.Add(self.keep_original_files_chk, 0, wx.ALL & (~wx.RIGHT) | wx.ALIGN_CENTER, self.FromDIP(6))
        keep_original_files_hbox.Add(keep_original_files_tip, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        override_lab = wx.StaticText(merge_option_box, -1, "存在同名文件时")
        self.override_option_choice = wx.Choice(merge_option_box, -1, choices = list(override_option_map.keys()))

        override_hbox = wx.BoxSizer(wx.HORIZONTAL)
        override_hbox.Add(override_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        override_hbox.Add(self.override_option_choice, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        merge_option_sbox = wx.StaticBoxSizer(merge_option_box, wx.VERTICAL)
        merge_option_sbox.Add(override_hbox, 0, wx.EXPAND)
        merge_option_sbox.Add(keep_original_files_hbox, 0, wx.EXPAND)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(ffmpeg_sbox, 0, wx.ALL | wx.EXPAND, self.FromDIP(6))
        vbox.Add(merge_option_sbox, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))

        self.panel.SetSizer(vbox)

        super().init_UI()

    def Bind_EVT(self):
        self.browse_btn.Bind(wx.EVT_BUTTON, self.onBrowsePathEVT)

        self.detect_btn.Bind(wx.EVT_BUTTON, self.onDetectEVT)

        self.tutorial_btn.Bind(wx.EVT_BUTTON, self.onTutorialEVT)

    def load_data(self):
        self.path_box.SetValue(Config.Merge.ffmpeg_path)
        self.check_ffmpeg_chk.SetValue(Config.Merge.ffmpeg_check_available_when_launch)
        
        self.override_option_choice.SetSelection(Config.Merge.override_option)
        self.keep_original_files_chk.SetValue(Config.Merge.keep_original_files)

    def save_data(self):
        Config.Merge.ffmpeg_path = self.path_box.GetValue()
        Config.Merge.ffmpeg_check_available_when_launch = self.check_ffmpeg_chk.GetValue()
        Config.Merge.override_option = self.override_option_choice.GetSelection()
        Config.Merge.keep_original_files = self.keep_original_files_chk.GetValue()

    def onValidate(self):
        if not self.path_box.GetValue():
            return self.warn("FFmpeg 路径无效")
        
        self.save_data()

    def onBrowsePathEVT(self, event: wx.CommandEvent):
        default_dir = os.path.dirname(self.path_box.GetValue())

        # 根据不同平台选取不同后缀名文件
        match Platform(Config.Sys.platform):
            case Platform.Windows:
                defaultFile = "ffmpeg.exe"
                wildcard = "FFmpeg|ffmpeg.exe"

            case Platform.Linux | Platform.macOS:
                defaultFile = "ffmpeg"
                wildcard = "FFmpeg|*"

        dlg = wx.FileDialog(self, "选择 FFmpeg 路径", defaultDir = default_dir, defaultFile = defaultFile, style = wx.FD_OPEN, wildcard = wildcard)

        if dlg.ShowModal() == wx.ID_OK:
            save_path = dlg.GetPath()
            self.path_box.SetValue(save_path)

        dlg.Destroy()

    def onDetectEVT(self, event: wx.CommandEvent):
        detect_window = DetectDialog(self)

        if detect_window.ShowModal() == wx.ID_OK:
            self.path_box.SetValue(detect_window.getPath())

    def onTutorialEVT(self, event: wx.CommandEvent):
        wx.LaunchDefaultBrowser("https://bili23.scott-sloan.cn/doc/install/ffmpeg.html")