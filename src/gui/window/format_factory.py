import wx
import os

from utils.config import Config

from utils.common.icon_v4 import Icon, IconID, IconSize
from utils.common.data_type import Callback, Process, PlayerCallback, RealTimeCallback
from utils.common.exception import GlobalExceptionInfo
from utils.common.directory import DirectoryUtils
from utils.common.map import time_ratio_map, ffmpeg_video_codec_map, ffmpeg_video_crf_map, ffmpeg_video_gpu_map, ffmpeg_audio_codec_map, ffmpeg_audio_samplerate_map, ffmpeg_audio_channel_map
from utils.common.re_utils import REUtils

from utils.module.ffmpeg_v2 import FFmpeg

from gui.dialog.error import ErrorInfoDialog

from gui.component.window.frame import Frame
from gui.component.panel.panel import Panel
from gui.component.button.large_bitmap_button import LargeBitmapButton
from gui.component.button.bitmap_button import BitmapButton
from gui.component.text_ctrl.text_ctrl import TextCtrl
from gui.component.text_ctrl.time_ctrl import TimeCtrl
from gui.component.player import Player, vlc_available
from gui.component.range_slider import RangeSlider

class SelectPage(Panel):
    def __init__(self, parent):
        Panel.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

    def init_UI(self):
        self.detail_info_btn = LargeBitmapButton(self, Icon.get_icon_bitmap(IconID.Info, icon_size = IconSize.MEDIUM), "详细信息")

        self.convertion_btn = LargeBitmapButton(self, Icon.get_icon_bitmap(IconID.Convert, icon_size = IconSize.MEDIUM), "格式转换")

        self.cutclip_btn = LargeBitmapButton(self, Icon.get_icon_bitmap(IconID.Cut, icon_size = IconSize.MEDIUM), "截取片段")

        self.extraction_btn = LargeBitmapButton(self, Icon.get_icon_bitmap(IconID.Audio, icon_size = IconSize.MEDIUM), "音频提取")

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.AddStretchSpacer()
        hbox.Add(self.detail_info_btn, 0, wx.ALL, self.FromDIP(6))
        hbox.Add(self.convertion_btn, 0, wx.ALL, self.FromDIP(6))
        hbox.Add(self.cutclip_btn, 0, wx.ALL, self.FromDIP(6))
        hbox.Add(self.extraction_btn, 0, wx.ALL, self.FromDIP(6))
        hbox.AddStretchSpacer()

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.AddStretchSpacer()
        vbox.Add(hbox, 0, wx.EXPAND)
        vbox.AddStretchSpacer()

        self.SetSizer(vbox)

    def Bind_EVT(self):
        self.detail_info_btn.onClickCustomEVT = self.onDetailInfoEVT
        self.convertion_btn.onClickCustomEVT = self.onConvertionEVT
        self.cutclip_btn.onClickCustomEVT = self.onCutClipEVT
        self.extraction_btn.onClickCustomEVT = self.onExtractionEVT

    def onDetailInfoEVT(self):
        self.change_drop_file_page(0)

    def onConvertionEVT(self):
        self.change_drop_file_page(1)

    def onCutClipEVT(self):
        self.change_drop_file_page(2)

    def onExtractionEVT(self):
        self.change_drop_file_page(3)

    def change_drop_file_page(self, page: int):
        parent = self.GetParent().GetParent().GetParent()

        parent.notebook.SetSelection(1)
        parent.set_target_page(page)

class DropFilePage(Panel):
    class FileDropTarget(wx.FileDropTarget):
        def __init__(self, parent):
            self.parent = parent

            wx.FileDropTarget.__init__(self)

        def OnDropFiles(self, x, y, filenames):
            self.parent.change_page(filenames[0])

            return True

    def __init__(self, parent):
        Panel.__init__(self, parent)

        self.Bind_EVT()

    def init_UI(self):
        file_drop_target = self.FileDropTarget(self)

        self.SetDropTarget(file_drop_target)

    def Bind_EVT(self):
        self.Bind(wx.EVT_PAINT, self.onPaintEVT)
        self.Bind(wx.EVT_LEFT_DOWN, self.onBrowseFileEVT)

    def onPaintEVT(self, event):
        dc = wx.PaintDC(self)

        self.draw_dashed_border(dc)
        self.draw_centered_text(dc)

    def onBrowseFileEVT(self, event):
        dlg = wx.FileDialog(self, "选择文件", defaultDir = Config.Download.path, style = wx.FD_OPEN)

        if dlg.ShowModal() == wx.ID_OK:
            parent = self.GetParent().GetParent().GetParent()

            parent.load_page(dlg.GetPath())
            
        dlg.Destroy()

    def draw_dashed_border(self, dc: wx.PaintDC):
        pen = wx.Pen(wx.SystemSettings.GetColour(wx.SYS_COLOUR_MENUTEXT), 2, wx.PENSTYLE_LONG_DASH)
        brush = wx.Brush(wx.SystemSettings.GetColour(wx.SYS_COLOUR_MENUBAR))

        dc.SetPen(pen)
        dc.SetBrush(brush)

        client_size = self.GetClientSize()

        rect = wx.Rect(self.FromDIP(10), self.FromDIP(10), client_size.width - self.FromDIP(20), client_size.height - self.FromDIP(20))

        dc.DrawRectangle(rect)
    
    def draw_centered_text(self, dc: wx.PaintDC):
        font = self.GetFont()
        font.SetFractionalPointSize(font.GetFractionalPointSize() + 2)

        dc.SetFont(font)

        text = ["将文件拖拽至此处", "或点击此处手动选择文件"]

        client_height = self.GetClientSize().height
        total_text_height = sum(dc.GetTextExtent(line).height for line in text) + self.FromDIP(4) * (len(text) - 1)
        y_start = (client_height - total_text_height) // 2

        for line in text:
            text_width, text_height = dc.GetTextExtent(line)
            x = (self.GetClientSize().width - text_width) // 2
            dc.DrawText(line, x, y_start)
            y_start += text_height + self.FromDIP(4)

class ContainerPage(Panel):
    class Page(Panel):
        def __init__(self, parent):
            Panel.__init__(self, parent)

            self.output_box: TextCtrl = None

        def init_utils(self):
            pass

        def onCloseEVT(self):
            pass

        def onChangeInputFile(self):
            pass
        
        def onBrowseEVT(self, event):
            dlg = wx.FileDialog(self, "选择保存位置", wildcard = self.wildcard, defaultDir = os.path.dirname(self.input_path), style = wx.FD_SAVE)

            if dlg.ShowModal() == wx.ID_OK:
                self.output_box.SetValue(dlg.GetPath())
                
            dlg.Destroy()

        def check(self):
            if not self.output_path:
                wx.MessageDialog(self, "缺少参数\n\n请指定输出文件目录", "警告", wx.ICON_WARNING).ShowModal()
                return True

        def get_callback(self, success_message: str):
            class callback(Callback):
                @staticmethod
                def onSuccess(*process):
                    def worker():
                        dlg = wx.MessageDialog(self, success_message, "提示", wx.ICON_INFORMATION | wx.YES_NO)
                        dlg.SetYesNoLabels("打开所在位置", "确定")

                        if dlg.ShowModal() == wx.ID_YES:
                            DirectoryUtils.open_file_location(self.output_path)

                        dlg.Destroy()

                    wx.CallAfter(worker)
                
                @staticmethod
                def onError(*process):
                    def worker():
                        dlg = ErrorInfoDialog(self, GlobalExceptionInfo.info)
                        dlg.ShowModal()

                    wx.CallAfter(worker)

            return callback
            
        @property
        def input_path(self) -> str:
            return self.GetParent().GetParent().input_path
        
        @property
        def input_format(self) -> str:
            _, ext = os.path.splitext(self.input_path)

            return ext.removeprefix(".")

        @property
        def output_path(self) -> str:
            return self.output_box.GetValue()

    class DetailInfoPage(Page):
        def __init__(self, parent):
            ContainerPage.Page.__init__(self, parent)

            self.init_UI()

        def init_UI(self):
            overall_box = wx.StaticBox(self, -1, "总体信息")

            self.duration_lab = wx.StaticText(overall_box, -1, "时长：")
            self.start_lab = wx.StaticText(overall_box, -1, "开始时间：")
            self.bitrate_lab = wx.StaticText(overall_box, -1, "比特率：")

            overall_sbox = wx.StaticBoxSizer(overall_box, wx.VERTICAL)
            overall_sbox.Add(self.duration_lab, 0, wx.ALL, self.FromDIP(6))
            overall_sbox.Add(self.start_lab, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
            overall_sbox.Add(self.bitrate_lab, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))

            video_box = wx.StaticBox(self, -1, "视频流信息")

            self.video_codec_lab = wx.StaticText(video_box, -1, "编码格式：")
            self.video_format_lab = wx.StaticText(video_box, -1, "格式：")
            self.resolution_lab = wx.StaticText(video_box, -1, "分辨率：")
            self.video_bitrate_lab = wx.StaticText(video_box, -1, "比特率：")
            self.fps_lab = wx.StaticText(video_box, -1, "帧速率：")

            video_sbox = wx.StaticBoxSizer(video_box, wx.VERTICAL)
            video_sbox.Add(self.video_codec_lab, 0, wx.ALL, self.FromDIP(6))
            video_sbox.Add(self.video_format_lab, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
            video_sbox.Add(self.resolution_lab, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
            video_sbox.Add(self.video_bitrate_lab, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
            video_sbox.Add(self.fps_lab, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))

            audio_box = wx.StaticBox(self, -1, "音频流信息")

            self.audio_codec_lab = wx.StaticText(audio_box, -1, "编码格式：")
            self.samplerate_lab = wx.StaticText(audio_box, -1, "采样率：")
            self.channel_lab = wx.StaticText(audio_box, -1, "声道：")
            self.sample_format_lab = wx.StaticText(audio_box, -1, "采样格式：")
            self.audio_bitrate_lab = wx.StaticText(audio_box, -1, "比特率：")

            audio_sbox = wx.StaticBoxSizer(audio_box, wx.VERTICAL)
            audio_sbox.Add(self.audio_codec_lab, 0, wx.ALL, self.FromDIP(6))
            audio_sbox.Add(self.samplerate_lab, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
            audio_sbox.Add(self.channel_lab, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
            audio_sbox.Add(self.sample_format_lab, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
            audio_sbox.Add(self.audio_bitrate_lab, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))

            stream_hbox = wx.BoxSizer(wx.HORIZONTAL)
            stream_hbox.Add(video_sbox, 1, wx.ALL | wx.EXPAND, self.FromDIP(6))
            stream_hbox.Add(audio_sbox, 1, wx.ALL & (~wx.LEFT) | wx.EXPAND, self.FromDIP(6))

            vbox = wx.BoxSizer(wx.VERTICAL)
            vbox.Add(overall_sbox, 0, wx.ALL | wx.EXPAND, self.FromDIP(6))
            vbox.Add(stream_hbox, 0, wx.EXPAND)

            self.SetSizer(vbox)

        def Bind_EVT(self):
            pass
        
        def get_file_info(self):
            class callback(Callback):
                @staticmethod
                def onSuccess(*process: Process):
                    info = FFmpeg.Utils.parse_info(process.output)

                    self.duration_lab.SetLabel(f"时长：{info.get('duration')}")
                    self.start_lab.SetLabel(f"开始时间：{info.get('start')}")
                    self.bitrate_lab.SetLabel(f"比特率：{info.get('bitrate')}")

                    self.video_codec_lab.SetLabel(f"编码格式：{info.get('vcodec')}")
                    self.video_format_lab.SetLabel(f"格式：{info.get('vformat')}")
                    self.resolution_lab.SetLabel(f"分辨率：{info.get('resolution')}")
                    self.video_bitrate_lab.SetLabel(f"比特率：{info.get('vbitrate')}")
                    self.fps_lab.SetLabel(f"帧速率：{info.get('fps')}")

                    self.audio_codec_lab.SetLabel(f"编码格式：{info.get('acodec')}")
                    self.samplerate_lab.SetLabel(f"采样率：{info.get('samplerate')}")
                    self.channel_lab.SetLabel(f"声道：{info.get('channel')}")
                    self.sample_format_lab.SetLabel(f"采样格式：{info.get('sampleformat')}")
                    self.audio_bitrate_lab.SetLabel(f"比特率：{info.get('abitrate')}")
                
                @staticmethod
                def onError(*process):
                    pass

            FFmpeg.Utils.info(self.input_path, callback)
        
        def onChangeInputFile(self):
            self.get_file_info()
        
    class ConvertionPage(Page):
        def __init__(self, parent):
            ContainerPage.Page.__init__(self, parent)

            self.init_UI()

            self.Bind_EVT()

        def init_UI(self):
            output_box = wx.StaticBox(self, -1, "输出设置")

            output_lab = wx.StaticText(output_box, -1, "输出")
            self.output_box = TextCtrl(output_box, -1)
            self.output_browse_btn = wx.Button(output_box, -1, "浏览", size = self.get_scaled_size((60, 24)))

            output_sbox = wx.StaticBoxSizer(output_box, wx.HORIZONTAL)
            output_sbox.Add(output_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
            output_sbox.Add(self.output_box, 1, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
            output_sbox.Add(self.output_browse_btn, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

            video_stream_box = wx.StaticBox(self, -1, "视频流设置")

            video_stream_codec_lab = wx.StaticText(video_stream_box, -1, "编码格式")
            self.video_stream_codec_choice = wx.Choice(video_stream_box, -1, choices = list(ffmpeg_video_codec_map.keys()))
            self.video_stream_codec_choice.SetStringSelection("AVC/H.264")

            video_stream_crf_lab = wx.StaticText(video_stream_box, -1, "CRF")
            self.video_stream_crf_choice = wx.Choice(video_stream_box, -1, choices = list(ffmpeg_video_crf_map.keys()))
            self.video_stream_crf_choice.SetStringSelection("关闭")

            video_stream_gpu_lab = wx.StaticText(video_stream_box, -1, "GPU")
            self.video_stream_gpu_choice = wx.Choice(video_stream_box, -1, choices = list(ffmpeg_video_gpu_map.keys()))
            self.video_stream_gpu_choice.SetStringSelection("自动检测")

            video_stream_bitrate_lab = wx.StaticText(video_stream_box, -1, "比特率")
            self.video_stream_bitrate_box = TextCtrl(video_stream_box, -1, "1500")
            video_stream_bitrate_unit_lab = wx.StaticText(video_stream_box, -1, "kb/s")

            video_stream_grid_box = wx.FlexGridSizer(4, 3, 0, 0)
            video_stream_grid_box.Add(video_stream_codec_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
            video_stream_grid_box.Add(self.video_stream_codec_choice, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))
            video_stream_grid_box.AddSpacer(0)
            video_stream_grid_box.Add(video_stream_crf_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
            video_stream_grid_box.Add(self.video_stream_crf_choice, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))
            video_stream_grid_box.AddSpacer(0)
            video_stream_grid_box.Add(video_stream_gpu_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
            video_stream_grid_box.Add(self.video_stream_gpu_choice, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))
            video_stream_grid_box.AddSpacer(0)
            video_stream_grid_box.Add(video_stream_bitrate_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
            video_stream_grid_box.Add(self.video_stream_bitrate_box, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))
            video_stream_grid_box.Add(video_stream_bitrate_unit_lab, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

            video_stream_sbox = wx.StaticBoxSizer(video_stream_box, wx.VERTICAL)
            video_stream_sbox.Add(video_stream_grid_box, 0, wx.EXPAND)

            audio_stream_box = wx.StaticBox(self, -1, "音频流设置")

            audio_stream_codec_lab = wx.StaticText(audio_stream_box, -1, "编码格式")
            self.audio_stream_codec_choice = wx.Choice(audio_stream_box, -1, choices = list(ffmpeg_audio_codec_map))
            self.audio_stream_codec_choice.SetStringSelection("AAC")

            audio_stream_samplerate_lab = wx.StaticText(audio_stream_box, -1, "采样率")
            self.audio_stream_samplerate_choice = wx.Choice(audio_stream_box, -1, choices = list(ffmpeg_audio_samplerate_map.keys()))
            self.audio_stream_samplerate_choice.SetStringSelection("44100 Hz")

            audio_stream_channel_lab = wx.StaticText(audio_stream_box, -1, "声道")
            self.audio_stream_channel_choice = wx.Choice(audio_stream_box, -1, choices = list(ffmpeg_audio_channel_map.keys()))
            self.audio_stream_channel_choice.SetStringSelection("2 (Stereo)")

            audio_stream_bitrate_lab = wx.StaticText(audio_stream_box, -1, "比特率")
            self.audio_stream_bitrate_box = TextCtrl(audio_stream_box, -1, "128")
            audio_stream_bitrate_unit_lab = wx.StaticText(audio_stream_box, -1, "kb/s")

            audio_stream_grid_box = wx.FlexGridSizer(4, 3, 0, 0)
            audio_stream_grid_box.Add(audio_stream_codec_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
            audio_stream_grid_box.Add(self.audio_stream_codec_choice, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))
            audio_stream_grid_box.AddSpacer(0)
            audio_stream_grid_box.Add(audio_stream_samplerate_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
            audio_stream_grid_box.Add(self.audio_stream_samplerate_choice, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))
            audio_stream_grid_box.AddSpacer(0)
            audio_stream_grid_box.Add(audio_stream_channel_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
            audio_stream_grid_box.Add(self.audio_stream_channel_choice, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))
            audio_stream_grid_box.AddSpacer(0)
            audio_stream_grid_box.Add(audio_stream_bitrate_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
            audio_stream_grid_box.Add(self.audio_stream_bitrate_box, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))
            audio_stream_grid_box.Add(audio_stream_bitrate_unit_lab, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

            audio_stream_sbox = wx.StaticBoxSizer(audio_stream_box, wx.VERTICAL)
            audio_stream_sbox.Add(audio_stream_grid_box, 0, wx.EXPAND)

            stream_hbox = wx.BoxSizer(wx.HORIZONTAL)
            stream_hbox.Add(video_stream_sbox, 1, wx.ALL, self.FromDIP(6))
            stream_hbox.Add(audio_stream_sbox, 1, wx.ALL & (~wx.LEFT), self.FromDIP(6))

            progress_box = wx.StaticBox(self, -1, "进度")

            self.progress_bar = wx.Gauge(self, -1, style = wx.GA_SMOOTH | wx.GA_TEXT)

            progress_sbox = wx.StaticBoxSizer(progress_box, wx.VERTICAL)
            progress_sbox.Add(self.progress_bar, 0, wx.ALL | wx.EXPAND, self.FromDIP(6))

            self.start_btn = wx.Button(self, -1, "开始转换", size =self.FromDIP((120, 28)))

            action_hbox = wx.BoxSizer(wx.HORIZONTAL)
            action_hbox.AddStretchSpacer()
            action_hbox.Add(self.start_btn, 0, wx.ALL, self.FromDIP(6))

            vbox = wx.BoxSizer(wx.VERTICAL)
            vbox.Add(output_sbox, 0, wx.ALL & (~wx.BOTTOM) | wx.EXPAND, self.FromDIP(6))
            vbox.Add(stream_hbox, 0, wx.EXPAND)
            vbox.Add(progress_sbox, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))
            vbox.Add(action_hbox, 0, wx.EXPAND)

            self.SetSizer(vbox)

        def Bind_EVT(self):
            self.output_browse_btn.Bind(wx.EVT_BUTTON, self.onBrowseEVT)

            self.video_stream_codec_choice.Bind(wx.EVT_CHOICE, self.onChangeVideoCodecEVT)
            self.audio_stream_codec_choice.Bind(wx.EVT_CHOICE, self.onChangeAudioCodecEVT)

            self.start_btn.Bind(wx.EVT_BUTTON, self.onStartEVT)
        
        def onChangeInputFile(self):
            self.output_box.SetValue("")

        def onChangeVideoCodecEVT(self, event):
            enable = self.video_stream_codec_choice.GetStringSelection() == "Copy"

            self.video_stream_crf_choice.Enable(enable)
            self.video_stream_gpu_choice.Enable(enable)

        def onChangeAudioCodecEVT(self, event):
            pass
        
        def onStartEVT(self, event):
            if self.check():
                return
            
            info = {
                "input_path": self.input_path,
                "output_path": self.output_path
            }

            FFmpeg.Utils.convert(info, self.get_callback("转换完成\n\n视频转换完成"))

        def get_callback(self, success_message: str):
            class callback(RealTimeCallback):
                @staticmethod
                def onReadOutput(output):
                    pass

                @staticmethod
                def onSuccess(*process):
                    def worker():
                        dlg = wx.MessageDialog(self, success_message, "提示", wx.ICON_INFORMATION | wx.YES_NO)
                        dlg.SetYesNoLabels("打开所在位置", "确定")

                        if dlg.ShowModal() == wx.ID_YES:
                            DirectoryUtils.open_file_location(self.output_path)

                        dlg.Destroy()

                    wx.CallAfter(worker)

                @staticmethod
                def onError(*process):
                    def worker():
                        dlg = ErrorInfoDialog(self, GlobalExceptionInfo.info)
                        dlg.ShowModal()

                    wx.CallAfter(worker)

            return callback

        @property
        def wildcard(self):
            return "媒体文件 | *.mp4;*.avi;*flv;*.mkv;*.mov;*.wmv;*.webm"
    
    class CutClipPage(Page):
        def __init__(self, parent):
            ContainerPage.Page.__init__(self, parent)

            self.init_UI()

            self.Bind_EVT()

        def init_UI(self):
            self.player = Player(self)
            
            bottom_line = wx.StaticLine(self, -1)

            self.range_slider = RangeSlider(self, -1, lowValue = 0, highValue = 100, minValue = 0, maxValue = 100)

            self.start_time_box = TimeCtrl(self, "开始时间")
            self.end_time_box = TimeCtrl(self, "结束时间")

            ratio_lab = wx.StaticText(self, -1, "精度")
            self.ratio_choice = wx.Choice(self, -1, choices = list(time_ratio_map.keys()))
            self.ratio_choice.SetSelection(0)

            ratio_hbox = wx.BoxSizer(wx.HORIZONTAL)
            ratio_hbox.Add(ratio_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
            ratio_hbox.Add(self.ratio_choice, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))

            ratio_vbox = wx.BoxSizer(wx.VERTICAL)
            ratio_vbox.AddStretchSpacer()
            ratio_vbox.Add(ratio_hbox, 0, wx.EXPAND)
            ratio_vbox.AddStretchSpacer()

            self.cut_btn = wx.Button(self, -1, "开始截取", size = self.get_scaled_size((100, 28)))

            time_hbox = wx.BoxSizer(wx.HORIZONTAL)
            time_hbox.Add(self.start_time_box, 0, wx.EXPAND)
            time_hbox.AddSpacer(self.FromDIP(20))
            time_hbox.Add(self.end_time_box, 0, wx.EXPAND)
            time_hbox.AddSpacer(self.FromDIP(20))
            time_hbox.Add(ratio_vbox, 0, wx.EXPAND)

            output_lab = wx.StaticText(self, -1, "输出")
            self.output_box = TextCtrl(self, -1)
            self.output_browse_btn = wx.Button(self, -1, "浏览", size = self.get_scaled_size((60, 24)))

            output_hbox = wx.BoxSizer(wx.HORIZONTAL)
            output_hbox.Add(output_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
            output_hbox.Add(self.output_box, 1, wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
            output_hbox.Add(self.output_browse_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
            output_hbox.AddStretchSpacer()
            output_hbox.Add(self.cut_btn, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))

            vbox = wx.BoxSizer(wx.VERTICAL)
            vbox.Add(self.player, 1, wx.EXPAND)
            vbox.Add(bottom_line, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM) | wx.EXPAND)
            vbox.Add(self.range_slider, 0, wx.ALL & (~wx.BOTTOM) | wx.EXPAND, self.FromDIP(6))
            vbox.Add(time_hbox, 0, wx.EXPAND)
            vbox.Add(output_hbox, 0, wx.EXPAND)

            self.SetSizer(vbox)

        def Bind_EVT(self):
            self.output_browse_btn.Bind(wx.EVT_BUTTON, self.onBrowseEVT)
            self.cut_btn.Bind(wx.EVT_BUTTON, self.onCutEVT)

            self.range_slider.Bind(wx.EVT_SLIDER, self.onSliderEVT)
            self.ratio_choice.Bind(wx.EVT_CHOICE, self.onChangeTimeRatio)

        def init_utils(self):
            class callback(PlayerCallback):
                @staticmethod
                def onLengthChange(length: int):
                    self.onLengthChange(length)

                @staticmethod
                def onReset():
                    self.onReset()
            
            self.player.init_player(callback)

        def onCloseEVT(self):
            self.player.close_player()

        def onChangeInputFile(self):
            if vlc_available:
                self.player.reset()

                self.player.set_playurl(self.input_path)

                self.output_box.SetValue("")

        def onSliderEVT(self, event):
            obj = event.GetEventObject()
            lv, hv = obj.GetValues()

            self.start_time_box.SetTime(int(round(lv) * self.time_ratio))
            self.end_time_box.SetTime(int(round(hv) * self.time_ratio))

        def onCutEVT(self, event):
            def get_info():
                return {
                    "input_path": self.input_path,
                    "output_path": self.output_path,
                    "start_time": self.start_time_box.GetValue(as_wxDateTime = True).Format("%H:%M:%S"),
                    "end_time": self.end_time_box.GetValue(as_wxDateTime = True).Format("%H:%M:%S")
                }

            if self.check():
                return

            FFmpeg.Utils.cut(get_info(), self.get_callback("截取完成\n\n截取片段完成"))

        def onLengthChange(self, length):
            self.range_slider.SetMax(int(length / self.time_ratio))
            self.range_slider.SetValues(0, int(length / self.time_ratio))

        def onReset(self):
            self.start_time_box.SetTime(0)
            self.end_time_box.SetTime(0)

            self.range_slider.SetMax(100)
            self.range_slider.SetValues(0, 100)

        def onChangeTimeRatio(self, event):
            self.onLengthChange(self.player.get_time())

        @property
        def wildcard(self):
            return f"{self.input_format.upper()} 文件 | *.{self.input_format}"

        @property
        def time_ratio(self):
            match self.ratio_choice.GetSelection():
                case 0:
                    return 100
                
                case 1:
                    return 500
                
                case 2:
                    return 1000

    class ExtractionPage(Page):
        def __init__(self, parent):
            ContainerPage.Page.__init__(self, parent)

            self.init_UI()

            self.Bind_EVT()

            self.acodec = ""
            self.output_format = ""

        def init_UI(self):
            output_lab = wx.StaticText(self, -1, "输出")
            self.output_box = TextCtrl(self, -1)
            self.output_browse_btn = wx.Button(self, -1, "浏览", size = self.get_scaled_size((60, 24)))

            output_hbox = wx.BoxSizer(wx.HORIZONTAL)
            output_hbox.Add(output_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
            output_hbox.Add(self.output_box, 1, wx.ALL & (~wx.LEFT), self.FromDIP(6))
            output_hbox.Add(self.output_browse_btn, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))

            self.audio_format_lab = wx.StaticText(self, -1, "音频流编码格式：--")
            self.target_format_lab = wx.StaticText(self, -1, "目标格式：--")

            format_hbox = wx.BoxSizer(wx.HORIZONTAL)
            format_hbox.Add(self.audio_format_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
            format_hbox.AddSpacer(self.FromDIP(40))
            format_hbox.Add(self.target_format_lab, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

            self.start_btn = wx.Button(self, -1, "开始分离", size = self.FromDIP((120, 28)))

            action_hbox = wx.BoxSizer(wx.HORIZONTAL)
            action_hbox.Add(format_hbox, 0, wx.EXPAND)
            action_hbox.AddStretchSpacer()
            action_hbox.Add(self.start_btn, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))

            vbox = wx.BoxSizer(wx.VERTICAL)
            vbox.Add(output_hbox, 0, wx.EXPAND)
            vbox.Add(action_hbox, 0, wx.EXPAND)

            self.SetSizer(vbox)
        
        def Bind_EVT(self):
            self.output_browse_btn.Bind(wx.EVT_BUTTON, self.onBrowseEVT)

            self.start_btn.Bind(wx.EVT_BUTTON, self.onStartEVT)

        def onStartEVT(self, event):
            if self.check():
                return

            info = {
                "input_path": self.input_path,
                "output_path": self.output_path
            }
                
            FFmpeg.Utils.extract_audio(info, self.get_callback("提取完成\n\n音频提取完成"))

        def onChangeInputFile(self):
            self.get_file_info()

            self.output_box.SetValue("")
        
        def get_file_info(self):
            class callback(Callback):
                @staticmethod
                def onSuccess(*process: Process):
                    info = FFmpeg.Utils.parse_info(process.output)

                    self.acodec = info.get("acodec")

                    result = REUtils.find_output_format(self.acodec)

                    self.set_output_format(result)

                    self.update_info()
                
                @staticmethod
                def onError(*process):
                    pass

            FFmpeg.Utils.info(self.input_path, callback)

        def update_info(self):
            self.output_box.Enable(bool(self.output_format))
            self.output_browse_btn.Enable(bool(self.output_format))
            self.start_btn.Enable(bool(self.output_format))

            self.audio_format_lab.SetLabel(f"音频流编码格式：{self.acodec}")
            self.target_format_lab.SetLabel(f"目标格式：{self.output_format}")

            self.Layout()

        def set_output_format(self, result: list):
            if result:
                self.output_format: str = result[0]

                if self.output_format.startswith("wma"):
                    self.output_format = "wma"

            else:
                self.output_format = None

        @property
        def wildcard(self):
            return f"{self.output_format.upper()} 文件 | *.{self.output_format}"

    def __init__(self, parent):
        Panel.__init__(self, parent)
        self.parent = self.GetParent().GetParent().GetParent()

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

    def init_UI(self):
        font = self.GetFont()
        font.SetFractionalPointSize(font.GetFractionalPointSize() + 3)

        self.back_icon = wx.StaticBitmap(self, -1, Icon.get_icon_bitmap(IconID.Back, icon_size = IconSize.SMALL))

        self.title_lab = wx.StaticText(self, -1, "Title")
        self.title_lab.SetFont(font)

        self.input_lab = wx.StaticText(self, -1, "当前选择文件：")
        self.browse_btn = BitmapButton(self, Icon.get_icon_bitmap(IconID.Folder))

        top_hbox = wx.BoxSizer(wx.HORIZONTAL)
        top_hbox.Add(self.back_icon, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        top_hbox.AddSpacer(self.FromDIP(6))
        top_hbox.Add(self.title_lab, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        top_hbox.AddStretchSpacer()
        top_hbox.Add(self.input_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        top_hbox.Add(self.browse_btn, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTRE, self.FromDIP(6))

        top_border = wx.StaticLine(self, -1)

        self.notebook = wx.Simplebook(self, -1)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(top_hbox, 0, wx.EXPAND)
        vbox.Add(top_border, 0, wx.EXPAND)
        vbox.Add(self.notebook, 1, wx.EXPAND)

        self.SetSizer(vbox)

    def Bind_EVT(self):
        self.back_icon.Bind(wx.EVT_LEFT_DOWN, self.onBackEVT)
        self.browse_btn.Bind(wx.EVT_BUTTON, self.onBrowseEVT)

    def init_utils(self):
        pass

    def onBackEVT(self, event):
        parent = self.GetParent().GetParent().GetParent()

        self.notebook.GetCurrentPage().onCloseEVT()

        parent.notebook.SetSelection(0)

    def onBrowseEVT(self, event):
        dlg = wx.FileDialog(self, "选择文件", defaultDir = os.path.dirname(self.input_path), defaultFile = os.path.basename(self.input_path), style = wx.FD_OPEN)

        if dlg.ShowModal() == wx.ID_OK:
            self.change_input_path(dlg.GetPath())
            
        dlg.Destroy()

    def change_input_path(self, path: str):
        self.parent.change_input_path(path)

        self.input_lab.SetLabel(f"当前选择文件：{os.path.basename(self.input_path)}")

        self.GetSizer().Layout()

    @property
    def input_path(self):
        return self.parent.input_path

class FormatFactoryWindow(Frame):
    def __init__(self, parent):
        Frame.__init__(self, parent, "视频工具箱")

        self.SetSize(self.FromDIP((850, 500)))

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

        self.CentreOnParent()

    def init_UI(self):
        self.panel = Panel(self)

        self.notebook = wx.Simplebook(self.panel, -1)

        self.select_page = SelectPage(self.notebook)
        self.drop_files_page = DropFilePage(self.notebook)
        self.container_page = ContainerPage(self.notebook)

        self.notebook.AddPage(self.select_page, "select action")
        self.notebook.AddPage(self.drop_files_page, "drop files")
        self.notebook.AddPage(self.container_page, "sub page")

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.notebook, 1, wx.EXPAND)

        self.panel.SetSizerAndFit(vbox)

    def Bind_EVT(self):
        self.Bind(wx.EVT_CLOSE, self.onCloseEVT)

    def init_utils(self):
        self.input_path = None
        self.input_format = None
        self.target_page = None
    
    def onCloseEVT(self, event):
        if self.container_page.notebook.GetPageCount():
            self.container_page.notebook.GetCurrentPage().onCloseEVT()

        event.Skip()

    def load_page(self, path: str):
        def load_container_page():
            def get_title():
                return {
                    0: "详细信息",
                    1: "格式转换",
                    2: "截取片段",
                    3: "音频分离",
                }.get(self.target_page)
            
            def get_page():
                match self.target_page:
                    case 0:
                        return self.container_page.DetailInfoPage(self.container_page.notebook)

                    case 1:
                        return self.container_page.ConvertionPage(self.container_page.notebook)

                    case 2:
                        return self.container_page.CutClipPage(self.container_page.notebook)

                    case 3:
                        return self.container_page.ExtractionPage(self.container_page.notebook)
                
            self.container_page.notebook.DeleteAllPages()

            self.container_page.notebook.AddPage(get_page(), "new")
            self.container_page.notebook.GetCurrentPage().init_utils()

            self.container_page.title_lab.SetLabel(get_title())

            self.container_page.change_input_path(self.input_path)

        self.set_input_path(path)

        load_container_page()

        self.notebook.SetSelection(2)

    def change_input_path(self, path: str):
        self.set_input_path(path)

        self.container_page.notebook.GetCurrentPage().onChangeInputFile()

    def set_input_path(self, path: str):
        self.input_path = path

    def set_target_page(self, page: int):
        self.target_page = page