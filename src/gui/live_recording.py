import wx
import os
import subprocess

from utils.live import LiveInfo
from utils.config import Config

class LiveRecordingWindow(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, "直播录制")

        self.init_UI()

        self.Bind_EVT()

        self.CenterOnParent()

        self.init_live_info()

    def init_UI(self):
        font: wx.Font = self.GetFont()
        font.SetPointSize(12)

        self.title_lab = wx.StaticText(self, -1)
        self.title_lab.SetFont(font)

        m3u8_link_lab = wx.StaticText(self, -1, "m3u8 链接")
        self.m3u8_link_box = wx.TextCtrl(self, -1, size = self.FromDIP((350, -1)))
        self.copy_link_btn = wx.Button(self, -1, "复制", size = self.FromDIP((60, 24)))

        recording_lab = wx.StaticText(self, -1, "保存位置")
        self.recording_path_box = wx.TextCtrl(self, -1, size = self.FromDIP((350, -1)))
        self.browse_path_btn = wx.Button(self, -1, "浏览", size = self.FromDIP((60, 24)))

        bag_box = wx.GridBagSizer(2, 3)
        bag_box.Add(m3u8_link_lab, pos = (0, 0), flag = wx.ALL | wx.ALIGN_CENTER, border = 10)
        bag_box.Add(self.m3u8_link_box, pos = (0, 1), flag = wx.ALL & (~wx.LEFT), border = 10)
        bag_box.Add(self.copy_link_btn, pos = (0, 2), flag = wx.ALL & (~wx.LEFT), border = 10)
        bag_box.Add(recording_lab, pos = (1, 0), flag = wx.ALL | wx.ALIGN_CENTER, border = 10)
        bag_box.Add(self.recording_path_box, pos = (1, 1), flag = wx.ALL & (~wx.LEFT), border = 10)
        bag_box.Add(self.browse_path_btn, pos = (1, 2), flag = wx.ALL & (~wx.LEFT), border = 10)

        self.start_recording_btn = wx.Button(self, -1, "开始录制", size = self.getButtonSize())
        self.open_player_btn = wx.Button(self, -1, "直接播放", size = self.getButtonSize())

        action_hbox = wx.BoxSizer(wx.HORIZONTAL)
        action_hbox.AddStretchSpacer()
        action_hbox.Add(self.open_player_btn, 0, wx.ALL, 10)
        action_hbox.Add(self.start_recording_btn, 0, wx.ALL & (~wx.LEFT), 10)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.title_lab, 0, wx.ALL, 10)
        vbox.Add(bag_box)
        vbox.Add(action_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def Bind_EVT(self):
        self.copy_link_btn.Bind(wx.EVT_BUTTON, self.onCopy)
        self.browse_path_btn.Bind(wx.EVT_BUTTON, self.onBrowse)

        self.open_player_btn.Bind(wx.EVT_BUTTON, self.onPlay)

    def init_live_info(self):
        self.title_lab.SetLabel(LiveInfo.title)

        self.m3u8_link_box.SetValue(LiveInfo.m3u8_link)

        path = os.path.join(Config.Download.path, f"{LiveInfo.title}.mp4")

        self.recording_path_box.SetValue(path)

    def onCopy(self, event):
        # 复制到剪切板
        if wx.TheClipboard.Open():
            wx.TheClipboard.SetData(wx.TextDataObject(self.m3u8_link_box.GetValue()))
            wx.TheClipboard.Close()

    def onBrowse(self, event):
        dlg = wx.FileDialog(self, "选择保存位置", defaultDir = Config.Download.path, defaultFile = LiveInfo.title, wildcard = "视频文件(*.mp4)|*.mp4", style = wx.FD_SAVE)

        if dlg.ShowModal() == wx.ID_OK:
            path = dlg.GetPath()
            self.recording_path_box.SetValue(path)

        dlg.Destroy()

    def onPlay(self, event):
        if not Config.Misc.player_path:
            wx.MessageDialog(self, "未配置播放器\n\n未配置播放器，请打开程序设置进行相关配置", "警告", wx.ICON_WARNING).ShowModal()
            return

        cmd = f'"{Config.Misc.player_path}" "{self.m3u8_link_box.GetValue()}"'

        subprocess.Popen(cmd, shell = True, stdout = subprocess.PIPE, stderr = subprocess.STDOUT)

    def getButtonSize(self):
        # 解决 Linux macOS 按钮太小的问题
        match Config.Sys.platform:
            case "windows":
                size = self.FromDIP((100, 30))
            case "linux" | "darwin":
                size = self.FromDIP((120, 40))

        return size
