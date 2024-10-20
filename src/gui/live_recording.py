import wx
import os
import re
import subprocess
from typing import List

from utils.live import LiveInfo
from utils.config import Config
from utils.thread import Thread
from utils.tools import format_size

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
        self.m3u8_link_box = wx.TextCtrl(self, -1, size = self.FromDIP((400, -1)))
        self.copy_link_btn = wx.Button(self, -1, "复制", size = self.FromDIP((60, 24)))

        recording_lab = wx.StaticText(self, -1, "保存位置")
        self.recording_path_box = wx.TextCtrl(self, -1, size = self.FromDIP((400, -1)))
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
        self.open_directory_btn = wx.Button(self, -1, "打开所在位置", size = self.getButtonSize())

        font: wx.Font = self.GetFont()
        font.SetPointSize(10)

        self.status_lab = wx.StaticText(self, -1, "状态：未开始录制")
        self.status_lab.SetFont(font)
        self.duration_lab = wx.StaticText(self, -1, "时长：00:00:00.00")
        self.duration_lab.SetFont(font)
        self.size_lab = wx.StaticText(self, -1, "大小：0 KB")
        self.size_lab.SetFont(font)
        self.speed_lab = wx.StaticText(self, -1, "速度：0.0x")
        self.speed_lab.SetFont(font)

        info_hbox = wx.BoxSizer(wx.HORIZONTAL)
        info_hbox.Add(self.status_lab, 1, wx.ALL & (~wx.BOTTOM), 10)
        info_hbox.Add(self.duration_lab, 1, wx.ALL & (~wx.BOTTOM), 10)
        info_hbox.Add(self.size_lab, 1, wx.ALL & (~wx.BOTTOM), 10)
        info_hbox.Add(self.speed_lab, 1, wx.ALL & (~wx.BOTTOM), 10)

        action_hbox = wx.BoxSizer(wx.HORIZONTAL)
        action_hbox.AddStretchSpacer()
        action_hbox.Add(self.open_directory_btn, 0, wx.ALL, 10)
        action_hbox.Add(self.open_player_btn, 0, wx.ALL & (~wx.LEFT), 10)
        action_hbox.Add(self.start_recording_btn, 0, wx.ALL & (~wx.LEFT), 10)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.title_lab, 0, wx.ALL, 10)
        vbox.Add(bag_box)
        vbox.Add(info_hbox, 0, wx.EXPAND)
        vbox.AddSpacer(10)
        vbox.Add(action_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def Bind_EVT(self):
        self.Bind(wx.EVT_CLOSE, self.onClose)

        self.copy_link_btn.Bind(wx.EVT_BUTTON, self.onCopy)
        self.browse_path_btn.Bind(wx.EVT_BUTTON, self.onBrowse)

        self.open_player_btn.Bind(wx.EVT_BUTTON, self.onPlay)
        self.start_recording_btn.Bind(wx.EVT_BUTTON, self.onStartRecording)
        self.open_directory_btn.Bind(wx.EVT_BUTTON, self.onOpenDirectory)

    def init_live_info(self):
        self.title_lab.SetLabel(LiveInfo.title)

        self.m3u8_link_box.SetValue(LiveInfo.m3u8_link)

        path = os.path.join(Config.Download.path, f"{LiveInfo.title}.mp4")

        self.recording_path_box.SetValue(path)

        self.start = False

    def onClose(self, event):
        if self.start:
            dlg = wx.MessageDialog(self, "是否结束录制\n\n当前正在录制直播，是否要结束录制？", "警告", wx.ICON_WARNING | wx.YES_NO)

            if dlg.ShowModal() == wx.ID_YES:
                self.terminate_ffmpeg_process()

                event.Skip()

                return
            
        event.Skip()

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

    def onStartRecording(self, event):
        if self.start:
            self.terminate_ffmpeg_process()
            
            self.setStatus(False)

            self.start = False

            return
        
        if not self.recording_path_box.GetValue():
            wx.MessageDialog(self, "未选择保存位置\n\n请选择保存位置", "警告", wx.ICON_WARNING).ShowModal()
            return

        recording_thread = Thread(target = self.onRecording)
        recording_thread.start()

        self.setStatus(True)

        self.status_lab.SetLabel("状态：准备开始录制")

        self.Layout()

    def onRecording(self):
        output_path = self.recording_path_box.GetValue()

        cmd = f'"{Config.FFmpeg.path}" -y -i "{LiveInfo.m3u8_link}" -c copy "{output_path}"'

        self.process = subprocess.Popen(cmd, stdout = subprocess.PIPE, stderr = subprocess.STDOUT, stdin = subprocess.PIPE, universal_newlines = True, encoding = "utf-8", shell = True, start_new_session = True)

        while True:
            output = self.process.stdout.readline()

            if self.process.poll() is not None:
                break

            if "time=" in output:
                duration = re.findall(r"time=(\d{2}:\d{2}:\d{2}\.\d{2})", output)
                size = re.findall(r"size=\s*(\d+)(KiB|kB)", output)
                speed = re.findall(r"speed=\s*(\d+\.\d+)x", output)

                wx.CallAfter(self.updateProgress, duration, size, speed)

        self.setStatus(False)

        self.status_lab.SetLabel("状态：录制结束")

    def onOpenDirectory(self, event):
        path = self.recording_path_box.GetValue()
        directory = os.path.dirname(path)

        if not os.path.exists(path):
            wx.MessageDialog(self, f"文件不存在\n\n无法打开文件：{os.path.basename(path)}\n\n文件不存在。", "警告", wx.ICON_WARNING).ShowModal()
            return

        match Config.Sys.platform:
            case "windows":
                cmd = f'explorer.exe /select,{path}'

            case "linux":
                cmd = f'xdg-open "{directory}"'

            case "darwin":
                cmd = f'open -R "{path}"'
        
        subprocess.Popen(cmd, cwd = directory, shell = True)

    def setStatus(self, status: bool):
        if status:
            self.start_recording_btn.SetLabel("停止录制")
        else:
            self.start_recording_btn.SetLabel("开始录制")

        self.start = status

    def updateProgress(self, duration: List[str], size: List[str], speed: List[str]):
        self.status_lab.SetLabel("状态：正在录制")

        if duration:
            self.duration_lab.SetLabel(f"时长：{duration[0]}")
        
        if size:
            self.size_lab.SetLabel(f"大小：{format_size(int(size[0][0]))}")

        if speed:
            self.speed_lab.SetLabel(f"速度：{speed[0]}x")

        self.Layout()

    def terminate_ffmpeg_process(self):
        # 向 ffmpeg 输入 q 来停止运行，强制终止 ffmpeg 进程将导致视频无法播放
        self.process.stdin.write("q")
        self.process.stdin.flush()

        self.process.kill()