import wx

from utils.config import Config
from utils.common.model.task_info import DownloadTaskInfo
from utils.common.style.icon_v4 import Icon, IconID
from utils.common.enums import Platform, DownloadStatus

from utils.module.pic.cover import Cover

from gui.dialog.error import ErrorInfoDialog

from gui.component.panel.panel import Panel
from gui.component.staticbitmap.staticbitmap import StaticBitmap
from gui.component.label.info_label import InfoLabel
from gui.component.button.bitmap_button import BitmapButton

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

        self.cover_bmp = StaticBitmap(self, size = self.FromDIP((112, 63)))
        self.cover_bmp.SetCursor(wx.Cursor(wx.CURSOR_HAND))
        self.cover_bmp.SetToolTip("查看封面")

        self.title_lab = wx.StaticText(self, -1, size = self.FromDIP((300, -1)), style = wx.ST_ELLIPSIZE_MIDDLE)

        self.video_quality_lab = InfoLabel(self, "--", size = self.FromDIP((85, -1)))
        self.video_codec_lab = InfoLabel(self, "--", size = self.FromDIP((85, -1)))
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
        self.Bind(wx.EVT_WINDOW_DESTROY, self.onDestroyEVT)

        self.cover_bmp.Bind(wx.EVT_LEFT_DOWN, self.onCoverEVT)
        self.speed_lab.Bind(wx.EVT_LEFT_DOWN, self.onErrorDialogEVT)

        self.pause_btn.Bind(wx.EVT_BUTTON, self.onPauseEVT)
        self.stop_btn.Bind(wx.EVT_BUTTON, self.onStopEVT)

    def init_utils(self):
        from gui.window.download.item_utils import Utils
        
        self.utils = Utils(self, self.task_info)

        self.panel_destroy = False
        self.show_info = False

    def onDestroyEVT(self, event: wx.CommandEvent):
        self.panel_destroy = True

        event.Skip()

    def onCoverEVT(self, event: wx.MouseEvent):
        Cover.view_cover(self.download_window, self.task_info.cover_url)

    def onErrorDialogEVT(self, event: wx.MouseEvent):
        if self.task_info.error_info:
            dlg = ErrorInfoDialog(self.download_window, self.task_info.error_info)
            dlg.ShowModal()

    def onPauseEVT(self, event: wx.CommandEvent):
        match DownloadStatus(self.task_info.status):
            case DownloadStatus.Waiting:
                self.utils.start_download()

            case DownloadStatus.Downloading:
                self.utils.pause_download()

            case DownloadStatus.Pause:
                self.utils.resume_download()

            case DownloadStatus.Complete:
                self.utils.open_file_location()

            case DownloadStatus.MergeError:
                self.utils.merge_video()

            case DownloadStatus.DownloadError:
                self.utils.start_download()

    def onStopEVT(self, event: wx.CommandEvent):
        self.utils.destroy_panel(remove_file = True, user_action = True)

    def get_progress_bar_size(self):
        match Platform(Config.Sys.platform):
            case Platform.Windows | Platform.macOS:
                return self.FromDIP((196, 16))
            
            case Platform.Linux:
                return self.FromDIP((196, 4))