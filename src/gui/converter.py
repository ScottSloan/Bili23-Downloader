import wx
import re
import os
import time
import subprocess

from utils.config import Config
from utils.thread import Thread
from utils.mapping import video_codec_mapping, supported_gpu_mapping

class ConverterWindow(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, "格式转换", style = wx.DEFAULT_FRAME_STYLE & (~wx.MINIMIZE_BOX) & (~wx.MAXIMIZE_BOX))

        self.init_UI()

        self.Bind_EVT()

        self.CenterOnParent()

        self.start = False

    def init_UI(self):
        input_lab = wx.StaticText(self, -1, "输入")
        self.input_box = wx.TextCtrl(self, -1, size = self.FromDIP((400, 24)))
        self.input_browse_btn = wx.Button(self, -1, "浏览", size = self.FromDIP((60, 24)))

        input_hbox = wx.BoxSizer(wx.HORIZONTAL)
        input_hbox.Add(input_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        input_hbox.Add(self.input_box, 1, wx.ALL & (~wx.LEFT), 10)
        input_hbox.Add(self.input_browse_btn, 0, wx.ALL & (~wx.LEFT), 10)

        output_lab = wx.StaticText(self, -1, "输出")
        self.output_box = wx.TextCtrl(self, -1, size = self.FromDIP((400, 24)))
        self.output_browse_btn = wx.Button(self, -1, "浏览", size = self.FromDIP((60, 24)))

        output_hbox = wx.BoxSizer(wx.HORIZONTAL)
        output_hbox.Add(output_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        output_hbox.Add(self.output_box, 1, wx.ALL & (~wx.LEFT), 10)
        output_hbox.Add(self.output_browse_btn, 0, wx.ALL & (~wx.LEFT), 10)

        self.target_format_lab = wx.StaticText(self, -1, "目标格式：---")

        target_codec_lab = wx.StaticText(self, -1, "编码器")
        self.target_codec_choice = wx.Choice(self, -1, choices = list(video_codec_mapping.keys()))

        target_bitrate_lab = wx.StaticText(self, -1, "比特率")
        self.target_bitrate_box = wx.TextCtrl(self, -1, "1500")
        target_bitrate_unit_lab = wx.StaticText(self, -1, "kbit/s")

        target_params_hbox = wx.BoxSizer(wx.HORIZONTAL)
        target_params_hbox.Add(self.target_format_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        target_params_hbox.AddSpacer(20)
        target_params_hbox.Add(target_codec_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        target_params_hbox.Add(self.target_codec_choice, 0, wx.ALL & (~wx.LEFT), 10)
        target_params_hbox.Add(target_bitrate_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        target_params_hbox.Add(self.target_bitrate_box, 0, wx.ALL & (~wx.LEFT), 10)
        target_params_hbox.Add(target_bitrate_unit_lab, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, 10)

        self.hwaccel_chk = wx.CheckBox(self, -1, "启用硬件加速")

        gpu_lab = wx.StaticText(self, -1, "GPU")
        self.gpu_choice = wx.Choice(self, -1, choices = self.getGPUList())

        extra_hbox = wx.BoxSizer(wx.HORIZONTAL)
        extra_hbox.Add(self.hwaccel_chk, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        extra_hbox.Add(gpu_lab, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, 10)
        extra_hbox.Add(self.gpu_choice, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, 10)
        
        self.progress_lab = wx.StaticText(self, -1, "进度：--")
        self.time_lab = wx.StaticText(self, -1, "耗时：--")

        progress_hbox = wx.BoxSizer(wx.HORIZONTAL)
        progress_hbox.Add(self.progress_lab, 0, wx.ALL & (~wx.BOTTOM) & (~wx.TOP) | wx.ALIGN_CENTER, 10)
        progress_hbox.Add(self.time_lab, 0, wx.ALL & (~wx.BOTTOM) & (~wx.TOP) | wx.ALIGN_CENTER, 10)

        self.progress_bar = wx.Gauge(self, -1, style = wx.GA_PROGRESS)

        self.start_btn = wx.Button(self, -1, "开始转换", size = self.FromDIP((110, 30)))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(input_hbox, 0, wx.EXPAND)
        vbox.Add(output_hbox, 0, wx.EXPAND)
        vbox.Add(target_params_hbox, 0, wx.EXPAND)
        vbox.Add(extra_hbox, 0, wx.EXPAND)
        vbox.Add(progress_hbox, 0, wx.EXPAND)
        vbox.Add(self.progress_bar, 0, wx.ALL | wx.EXPAND, 10)
        vbox.Add(self.start_btn, 0, wx.ALL | wx.ALIGN_RIGHT, 10)

        self.SetSizerAndFit(vbox)

    def Bind_EVT(self):
        self.start_btn.Bind(wx.EVT_BUTTON, self.onStart)

        self.input_browse_btn.Bind(wx.EVT_BUTTON, self.onBrowseInputPath)
        self.output_browse_btn.Bind(wx.EVT_BUTTON, self.onBrowseOutputPath)

    def onStart(self, event):
        if self.start:
            self.process.kill()
            self.setStatus(False)
            return

        if not self.input_box.GetValue():
            wx.MessageDialog(self, "未选择输入文件\n\n请选择输入文件", "警告", wx.ICON_WARNING).ShowModal()
            return

        if not self.output_box.GetValue():
            wx.MessageDialog(self, "未选择输出文件\n\n请选择输出文件", "警告", wx.ICON_WARNING).ShowModal()
            return
        
        if self.target_codec_choice.GetSelection() == -1:
            wx.MessageDialog(self, "未选择编码器\n\n请选择编码器", "警告", wx.ICON_WARNING).ShowModal()
            return
        
        if not self.target_bitrate_box.GetValue():
            wx.MessageDialog(self, "未指定比特率\n\n请指定比特率，默认为 1500 kbps", "警告", wx.ICON_WARNING).ShowModal()
            return
        
        if self.gpu_choice.GetSelection() == -1 and self.hwaccel_chk.GetValue():
            wx.MessageDialog(self, "未选择 GPU 类型\n\n请选择 GPU 类型，根据设备实际情况选择，错误选择将导致转换失败", "警告", wx.ICON_WARNING).ShowModal()
            return

        convert_thread = Thread(target = self.startConvert)
        convert_thread.start()

        self.setStatus(True)

    def onBrowseInputPath(self, event):
        dlg = wx.FileDialog(self, "选择输入文件", style = wx.FD_OPEN, wildcard = "视频文件|*.3gp;*.asf;*.avi;*.dat;*.flv;*.m4v;*.mkv;*.mov;*.mp4;*.mpg;*.mpeg;*.ogg;*.rm;*.rmvb;*.vob;*.wmv")

        if dlg.ShowModal() == wx.ID_OK:
            save_path = dlg.GetPath()

            if save_path == self.output_box.GetValue():
                wx.MessageDialog(self, "文件已存在\n\n无法覆盖原文件，请指定新的文件名", "警告", wx.ICON_WARNING).ShowModal()
                return
            
            self.input_box.SetValue(save_path)

        dlg.Destroy()

    def onBrowseOutputPath(self, event):
        input_path = self.input_box.GetValue()
        file = self.getNewFileName(os.path.basename(input_path))

        dlg = wx.FileDialog(self, "保存输出文件", style = wx.FD_SAVE, defaultFile = file, defaultDir = os.path.dirname(input_path), wildcard = "视频文件|*.3gp;*.asf;*.avi;*.dat;*.flv;*.m4v;*.mkv;*.mov;*.mp4;*.mpg;*.mpeg;*.ogg;*.rm;*.rmvb;*.vob;*.wmv")

        if dlg.ShowModal() == wx.ID_OK:
            save_path = dlg.GetPath()

            if save_path == self.input_box.GetValue():
                wx.MessageDialog(self, "文件已存在\n\n无法覆盖原文件，请指定新的文件名", "警告", wx.ICON_WARNING).ShowModal()
                return
            
            self.output_box.SetValue(save_path)

            self.target_format_lab.SetLabel(f"目标格式：{os.path.splitext(save_path)[-1][1:]}")

            self.panel.Layout()

        dlg.Destroy()

    def startConvert(self):
        input_path = self.input_box.GetValue()
        output_path = self.output_box.GetValue()
        encoder = self.getEncoder()
        bitrate = self.target_bitrate_box.GetValue() + "k"

        cmd = f'"{Config.FFmpeg.path}" -y -i "{input_path}" -c:v {encoder} -b:v {bitrate} -strict experimental "{output_path}"'

        self.process = subprocess.Popen(cmd, stdout = subprocess.PIPE, stderr = subprocess.STDOUT, universal_newlines = True, encoding = "utf-8", shell = True)

        duration = None
        time_1 = time.time()

        while True:
            output = self.process.stdout.readline()

            if self.process.poll() is not None:
                break

            if "Duration" in output:
                duration_match = re.search(r"Duration: (\d{2}):(\d{2}):(\d{2})", output)

                if duration_match:
                    hours, minutes, seconds = map(int, duration_match.groups())
                    duration = hours * 3600 + minutes * 60 + seconds

            if "time=" in output and duration:
                time_match = re.search(r"time=(\d{2}):(\d{2}):(\d{2})", output)

                if time_match:
                    current_time = sum(int(x) * 60 ** i for i, x in enumerate(reversed(time_match.groups())))
                    progress = int(current_time / duration * 100)

                    self.progress_bar.SetValue(progress)
                    self.progress_lab.SetLabel(f"进度：{progress}%")
                    self.time_lab.SetLabel(f"耗时：{int(time.time() - time_1)}s")

                    self.panel.Layout()
    
        self.process.stdout.close()

        if self.process.returncode != 0:
            wx.MessageDialog(self, "视频转换失败\n\n在视频转换时出现问题，请检查：\n1.输入文件是否损坏\n2.若开启 GPU 加速，请检查 GPU 类型是否选择正确，驱动是否安装，GPU 是否支持加速\n3.若您使用的 FFmpeg 版本并非程序自带版本，请检查是否支持相关加速编码器", "警告", wx.ICON_WARNING).ShowModal()
            self.setStatus(False)
            self.resetProgress()
            return

        if not self.start:
            self.resetProgress()
            return

        self.convertComplete()

        self.setStatus(False)

    def convertComplete(self):
        self.progress_bar.SetValue(100)
        self.progress_lab.SetLabel("进度：100%")

        self.panel.Layout()

        dlg = wx.MessageDialog(self, "视频转换完成\n\n视频转换已完成", "提示", wx.ICON_INFORMATION | wx.YES_NO)
        dlg.SetYesNoLabels("打开文件夹", "确定")

        if dlg.ShowModal() == wx.ID_YES:
            os.startfile(os.path.dirname(self.output_box.GetValue()))

    def getEncoder(self):
        match Config.Sys.platform:
            case "windows" | "linux":
                if self.hwaccel_chk.GetValue():
                    match self.gpu_choice.GetSelection():
                        case 0:
                            return self.getNVAccels()
                        case 1:
                            return self.getAMDAaccels()
                        case 2:
                            return self.getINTELAccels()
                else:
                    match self.target_codec_choice.GetSelection():
                        case 0:
                            return "libx264"
                        
                        case 1:
                            return "libx265"
                        
                        case 2:
                            return "libaom-av1"
            case "darwin":
                if self.hwaccel_chk.GetValue():
                    return self.getMACAccels()
                else:
                    match self.target_codec_choice.GetSelection():
                        case 0:
                            return "libx264"
                        
                        case 1:
                            return "libx265"
                        
                        case 2:
                            return "libaom-av1"

    def getNVAccels(self):
        match self.target_codec_choice.GetSelection():
            case 0:
                return "h264_nvenc"
            
            case 1:
                return "hevc_nvenc"

            case 2:
                return "av1_nvenc"
            
    def getAMDAaccels(self):
        match self.target_codec_choice.GetSelection():
            case 0:
                return "h264_amf"
            
            case 1:
                return "hevc_amf"

            case 2:
                return "av1_amf"
            
    def getINTELAccels(self):
        match self.target_codec_choice.GetSelection():
            case 0:
                return "h264_qsv"
            
            case 1:
                return "hevc_qsv"

            case 2:
                return "av1_qsv"
    
    def getMACAccels(self):
        match self.target_codec_choice.GetSelection():
            case 0:
                return "h264_videotoolbox"
            
            case 1:
                return "hevc_videotoolbox"

            case 2:
                return ""
            
    def setStatus(self, status):
        if status:
            self.start_btn.SetLabel("停止")
            self.start = True
        else:
            self.start_btn.SetLabel("开始转换")
            self.start = False
    
    def resetProgress(self):
        self.progress_bar.SetValue(0)
        self.progress_lab.SetLabel("进度：--")
        self.time_lab.SetLabel("耗时：--")

        self.panel.Layout()

    def getNewFileName(self, filename: str):
        new_filename = list(filename)
        new_filename.insert(filename.rfind("."), "_out")

        return "".join(new_filename)
    
    def getGPUList(self):
        match Config.Sys.platform:
            case "windows" | "linux":
                return list(supported_gpu_mapping.keys())
            
            case "darwin":
                return ["VideoToolBox"]
    