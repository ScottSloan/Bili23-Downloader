import wx

from utils.config import Config

from utils.common.data_type import DownloadTaskInfo
from utils.common.enums import Platform, ParseType
from utils.common.icon_v4 import Icon, IconID
from utils.common.map import extra_map, video_quality_map, video_codec_map, audio_quality_map, get_mapping_key_by_value
from utils.common.formatter import FormatUtils

from gui.component.label.info_label import InfoLabel
from gui.component.button.bitmap_button import BitmapButton

from gui.component.panel.panel import Panel

class Utils:
    class UI:
        def __init__(self, parent: wx.Window):
            self.parent: DownloadTaskItemPanel = parent

        def show_cover(self, cover_url: str):
            pass

        def set_title(self, title: str):
            self.parent.title_lab.SetLabel(title)
            self.parent.title_lab.SetToolTip(title)

        def set_progress(self, progress: int):
            self.parent.progress_bar.SetValue(progress)
            self.parent.progress_bar.SetToolTip(f"{progress}%")

        def set_quality_label(self, label: str):
            self.parent.video_quality_lab.SetLabel(label)

        def set_codec_label(self, label: str):
            self.parent.video_codec_lab.SetLabel(label)

        def set_size_label(self, label: str):
            self.parent.video_size_lab.SetLabel(label)

    class Info:
        def __init__(self, task_info: DownloadTaskInfo):
            self.task_info = task_info

        def get_quality_label(self):
            match ParseType(self.task_info.download_type):
                case ParseType.Video | ParseType.Bangumi | ParseType.Cheese:
                    if "video" in self.task_info.download_option:
                        return get_mapping_key_by_value(video_quality_map, self.task_info.video_quality_id, "--")
                    else:
                        return "音频"

                case ParseType.Extra:
                    return " ".join([value for key, value in extra_map.items() if self.task_info.extra_option.get(key)])
                
                case _:
                    return "未知"
                
        def get_codec_label(self):
            match ParseType(self.task_info.download_type):
                case ParseType.Video | ParseType.Bangumi | ParseType.Cheese:
                    if "video" in self.task_info.download_option:
                        return get_mapping_key_by_value(video_codec_map, self.task_info.video_codec_id, "--")
                    else:
                        return get_mapping_key_by_value(audio_quality_map, self.task_info.audio_quality_id, "--")
                
                case _:
                    return ""

        def get_size_label(self):
            if self.task_info.progress == 100:
                return FormatUtils.format_size(self.task_info.total_file_size)
            
            elif self.task_info.total_file_size:
                return f"{FormatUtils.format_size(self.task_info.total_downloaded_size)}/{FormatUtils.format_size(self.task_info.total_file_size)}"
            
            else:
                return "--"
            
    def __init__(self, parent: wx.Window, task_info: DownloadTaskInfo):
        self.parent: DownloadTaskItemPanel = parent
        self.task_info = task_info

        self.ui = self.UI(parent)
        self.info = self.Info(task_info)

    def show_task_info(self):
        self.ui.show_cover(self.task_info.cover_url)

        self.ui.set_title(self.task_info.title)
        self.ui.set_progress(self.task_info.progress)

        self.ui.set_quality_label(self.info.get_quality_label())
        self.ui.set_codec_label(self.info.get_codec_label())
        self.ui.set_size_label(self.info.get_size_label())

        self.parent.Layout()

class DownloadTaskItemPanel(Panel):
    def __init__(self, parent: wx.Window, task_info: DownloadTaskInfo, download_window: wx.Window):
        from gui.window.download.download_v4 import DownloadManagerWindow

        self.task_info = task_info
        self.download_window: DownloadManagerWindow = download_window

        Panel.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

    def init_UI(self):
        self.set_dark_mode()

        self.cover_bmp = wx.StaticBitmap(self, -1, size = self.FromDIP((112, 63)))
        self.cover_bmp.SetCursor(wx.Cursor(wx.CURSOR_HAND))
        self.cover_bmp.SetToolTip("查看封面")

        self.title_lab = wx.StaticText(self, -1, size = self.FromDIP((300, 24)), style = wx.ST_ELLIPSIZE_MIDDLE)

        self.video_quality_lab = InfoLabel(self, "--", size = self.FromDIP((85, 16)))
        self.video_codec_lab = InfoLabel(self, "--", size = self.FromDIP((85, 16)))
        self.video_size_lab = InfoLabel(self, "--", size = self.FromDIP((-1, -1)))

        video_info_hbox = wx.BoxSizer(wx.HORIZONTAL)

        video_info_hbox.Add(self.video_quality_lab, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM) | wx.ALIGN_CENTER | wx.ALIGN_LEFT, 10)
        video_info_hbox.Add(self.video_codec_lab, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT) & (~wx.BOTTOM) | wx.ALIGN_CENTER | wx.ALIGN_LEFT, 10)
        video_info_hbox.Add(self.video_size_lab, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT) & (~wx.BOTTOM) | wx.ALIGN_CENTER | wx.ALIGN_LEFT, 10)

        video_info_vbox = wx.BoxSizer(wx.VERTICAL)
        video_info_vbox.AddSpacer(self.FromDIP(10))
        video_info_vbox.Add(self.title_lab, 0, wx.ALL & (~wx.BOTTOM) & (~wx.TOP) | wx.EXPAND, 10)
        video_info_vbox.AddStretchSpacer()
        video_info_vbox.Add(video_info_hbox, 0, wx.EXPAND)
        video_info_vbox.AddSpacer(self.FromDIP(8))

        self.progress_bar = wx.Gauge(self, -1, 100, size = self.get_progress_bar_size(), style = wx.GA_SMOOTH)

        progress_bar_hbox = wx.BoxSizer(wx.HORIZONTAL)
        progress_bar_hbox.Add(self.progress_bar, 0, wx.ALL & (~wx.BOTTOM) & (~wx.TOP) | wx.ALIGN_CENTER, 10)

        self.speed_lab = InfoLabel(self, "等待下载...", size = self.FromDIP((-1, -1)))

        speed_hbox = wx.BoxSizer(wx.HORIZONTAL)
        speed_hbox.Add(self.speed_lab, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM) | wx.ALIGN_CENTER, 10)

        progress_bar_vbox = wx.BoxSizer(wx.VERTICAL)
        progress_bar_vbox.AddSpacer(self.FromDIP(10 if Config.Sys.platform != Platform.Linux.value else 20))
        progress_bar_vbox.Add(progress_bar_hbox, 0, wx.EXPAND)
        progress_bar_vbox.AddStretchSpacer()
        progress_bar_vbox.Add(speed_hbox, 0, wx.EXPAND)
        progress_bar_vbox.AddSpacer(self.FromDIP(8))

        self.pause_btn = BitmapButton(self, Icon.get_icon_bitmap(IconID.Play))
        self.pause_btn.SetToolTip("开始下载")

        self.stop_btn = BitmapButton(self, Icon.get_icon_bitmap(IconID.Close))
        self.stop_btn.SetToolTip("取消下载")

        panel_hbox = wx.BoxSizer(wx.HORIZONTAL)
        panel_hbox.Add(self.cover_bmp, 0, wx.ALL, self.FromDIP(6))
        panel_hbox.Add(video_info_vbox, 0, wx.EXPAND)
        panel_hbox.AddStretchSpacer()
        panel_hbox.Add(progress_bar_vbox, 0, wx.EXPAND)
        panel_hbox.Add(self.pause_btn, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        panel_hbox.Add(self.stop_btn, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        panel_hbox.AddSpacer(self.FromDIP(6))

        bottom_border = wx.StaticLine(self, -1, style = wx.LI_HORIZONTAL)

        self.panel_vbox = wx.BoxSizer(wx.VERTICAL)
        self.panel_vbox.Add(panel_hbox, 1, wx.EXPAND)
        self.panel_vbox.Add(bottom_border, 0, wx.EXPAND)

        self.SetSizer(self.panel_vbox)
    
    def Bind_EVT(self):
        self.Bind(wx.EVT_WINDOW_DESTROY, self.onDestoryEVT)

        self.pause_btn.Bind(wx.EVT_BUTTON, self.onPauseEVT)
        self.stop_btn.Bind(wx.EVT_BUTTON, self.onStopEVT)

    def init_utils(self):
        self.utils = Utils(self, self.task_info)

        self.panel_destory = False

    def onDestoryEVT(self, event):
        self.panel_destory = True

        event.Skip()

    def onPauseEVT(self, event):
        pass

    def onStopEVT(self, event):
        self.task_info.remove_file()

        self.Destroy()

        self.download_window.update_title(self.task_info.source)

    def get_progress_bar_size(self):
        match Platform(Config.Sys.platform):
            case Platform.Windows | Platform.macOS:
                return self.FromDIP((196, 16))
            
            case Platform.Linux:
                return self.FromDIP((196, 4))