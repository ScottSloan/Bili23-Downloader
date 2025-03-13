import os
import wx
from io import BytesIO
from typing import Callable

from utils.common.icon_v2 import IconManager, IconType
from utils.common.data_type import DownloadTaskInfo, TaskPanelCallback, DownloaderCallback, MergeCallback
from utils.common.enums import DownloadOption, DownloadStatus
from utils.common.map import video_quality_map, audio_quality_map, video_codec_map, get_mapping_key_by_value
from utils.common.cache import DataCache
from utils.common.thread import Thread

from utils.module.ffmpeg import FFmpeg
from utils.module.downloader_v2 import Downloader
from utils.parse.download import DownloadParser
from utils.config import Config
from utils.tool_v2 import FormatTool, DownloadFileTool, RequestTool, FileDirectoryTool

from gui.templates import InfoLabel
from gui.dialog.cover import CoverViewerDialog

class EmptyItemPanel(wx.Panel):
    def __init__(self, parent, name: str):
        self.name = name

        wx.Panel.__init__(self, parent, -1)

        self.init_UI()

    def init_UI(self):
        self.empty_lab = wx.StaticText(self, -1, f"没有{self.name}的项目")

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.AddStretchSpacer()
        hbox.Add(self.empty_lab, 0, wx.ALL, 10)
        hbox.AddStretchSpacer()

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.AddStretchSpacer()
        vbox.Add(hbox, 0, wx.EXPAND)
        vbox.AddStretchSpacer()

        self.SetSizer(vbox)

    def destroy_panel(self):
        self.Hide()
        self.Destroy()

class LoadingItemPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        self.init_UI()

    def init_UI(self):
        self.loading_lab = wx.StaticText(self, -1, "正在加载中，请稍候")

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.AddStretchSpacer()
        hbox.Add(self.loading_lab, 0, wx.ALL, 10)
        hbox.AddStretchSpacer()

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.AddStretchSpacer()
        vbox.Add(hbox, 0, wx.EXPAND)
        vbox.AddStretchSpacer()

        self.SetSizer(vbox)

    def destroy_panel(self):
        self.Hide()
        self.Destroy()

class LoadMoreTaskItemPanel(wx.Panel):
    def __init__(self, parent, count: int, callback: Callable):
        self.count, self.callback = count, callback

        wx.Panel.__init__(self, parent, -1)

        self.init_UI()

        self.Bind_EVT()

    def init_UI(self):
        self.more_lab = wx.StaticText(self, -1, f"显示更多项目({self.count}+)")
        self.more_lab.SetCursor(wx.Cursor(wx.Cursor(wx.CURSOR_HAND)))
        
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.AddStretchSpacer()
        hbox.Add(self.more_lab, 0, wx.ALL, 10)
        hbox.AddStretchSpacer()

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(hbox, 0, wx.EXPAND)

        self.SetSizer(vbox)
    
    def Bind_EVT(self):
        self.more_lab.Bind(wx.EVT_LEFT_DOWN, self.onShowMoreEVT)

    def onShowMoreEVT(self, event):
        self.destroy_panel()

        self.callback()

    def destroy_panel(self):
        self.Hide()
        self.Destroy()

class DownloadTaskItemPanel(wx.Panel):
    def __init__(self, parent, info: DownloadTaskInfo, callback: TaskPanelCallback, download_window):
        self.task_info, self.callback, self.download_window = info, callback, download_window

        wx.Panel.__init__(self, parent, -1)

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

    def init_UI(self):
        self.icon_manager = IconManager(self)

        self.cover_bmp = wx.StaticBitmap(self, -1, size = self.FromDIP((112, 63)))
        self.cover_bmp.SetCursor(wx.Cursor(wx.CURSOR_HAND))
        self.cover_bmp.SetToolTip("查看封面")

        self.title_lab = wx.StaticText(self, -1, size = self.FromDIP((300, 24)), style = wx.ST_ELLIPSIZE_MIDDLE)

        self.video_quality_lab = InfoLabel(self, "--", size = self.FromDIP((-1, -1)))
        self.video_codec_lab = InfoLabel(self, "--", size = self.FromDIP((-1, -1)))
        self.video_size_lab = InfoLabel(self, "--", size = self.FromDIP((-1, -1)))

        video_info_hbox = wx.BoxSizer(wx.HORIZONTAL)

        video_info_hbox.Add(self.video_quality_lab, 1, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER | wx.ALIGN_LEFT, 10)
        video_info_hbox.Add(self.video_codec_lab, 1, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER | wx.ALIGN_LEFT, 10)
        video_info_hbox.Add(self.video_size_lab, 1, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER | wx.ALIGN_LEFT, 10)

        video_info_vbox = wx.BoxSizer(wx.VERTICAL)
        video_info_vbox.AddSpacer(5)
        video_info_vbox.Add(self.title_lab, 0, wx.ALL & (~wx.BOTTOM) | wx.EXPAND, 10)
        video_info_vbox.AddStretchSpacer()
        video_info_vbox.Add(video_info_hbox, 0, wx.EXPAND)
        video_info_vbox.AddSpacer(5)

        self.progress_bar = wx.Gauge(self, -1, 100, size = (-1, -1), style = wx.GA_SMOOTH)

        progress_bar_hbox = wx.BoxSizer(wx.HORIZONTAL)
        progress_bar_hbox.Add(self.progress_bar, 0, wx.ALL & (~wx.BOTTOM) | wx.ALIGN_CENTER, 10)

        self.speed_lab = InfoLabel(self, "等待下载...", size = self.FromDIP((-1, -1)))

        speed_hbox = wx.BoxSizer(wx.HORIZONTAL)
        speed_hbox.Add(self.speed_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, 10)

        progress_bar_vbox = wx.BoxSizer(wx.VERTICAL)
        progress_bar_vbox.AddSpacer(5)
        progress_bar_vbox.Add(progress_bar_hbox, 0, wx.EXPAND)
        progress_bar_vbox.AddStretchSpacer()
        progress_bar_vbox.Add(speed_hbox, 0, wx.EXPAND)
        progress_bar_vbox.AddSpacer(5)

        self.pause_btn = wx.BitmapButton(self, -1, self.icon_manager.get_icon_bitmap(IconType.RESUME_ICON), size = self.FromDIP((24, 24)))
        self.pause_btn.SetToolTip("开始下载")

        self.stop_btn = wx.BitmapButton(self, -1, self.icon_manager.get_icon_bitmap(IconType.DELETE_ICON), size = self.FromDIP((24, 24)))
        self.stop_btn.SetToolTip("取消下载")

        panel_hbox = wx.BoxSizer(wx.HORIZONTAL)
        panel_hbox.Add(self.cover_bmp, 0, wx.ALL, 10)
        panel_hbox.Add(video_info_vbox, 0, wx.EXPAND)
        panel_hbox.AddStretchSpacer()
        panel_hbox.Add(progress_bar_vbox, 0, wx.EXPAND)
        panel_hbox.Add(self.pause_btn, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        panel_hbox.Add(self.stop_btn, 0, wx.ALIGN_CENTER | wx.ALL, 10)
        panel_hbox.AddSpacer(10)

        bottom_border = wx.StaticLine(self, -1, style = wx.LI_HORIZONTAL)

        self.panel_vbox = wx.BoxSizer(wx.VERTICAL)
        self.panel_vbox.Add(panel_hbox, 1, wx.EXPAND)
        self.panel_vbox.Add(bottom_border, 0, wx.EXPAND)

        self.SetSizer(self.panel_vbox)

    def Bind_EVT(self):
        self.Bind(wx.EVT_WINDOW_DESTROY, self.onDestroyEVT)

        self.cover_bmp.Bind(wx.EVT_LEFT_DOWN, self.onViewCoverEVT)
        self.pause_btn.Bind(wx.EVT_BUTTON, self.onPauseEVT)
        self.stop_btn.Bind(wx.EVT_BUTTON, self.onStopEVT)

    def init_utils(self):
        self._show_cover = False
        self._destroy = False

        self.file_tool = DownloadFileTool(self.task_info.id)

        self.show_task_info()

        self.set_download_status(self.task_info.status)

    def show_task_info(self):
        self.title_lab.SetLabel(self.task_info.title)
        self.title_lab.SetToolTip(self.task_info.title)

        self.progress_bar.SetValue(self.task_info.progress)
        self.progress_bar.SetToolTip(f"{self.task_info.progress}%")

        if self.task_info.download_option == DownloadOption.OnlyAudio.value:
            self.video_quality_lab.SetLabel("音频")
            self.video_codec_lab.SetLabel(get_mapping_key_by_value(audio_quality_map, self.task_info.audio_quality_id, "--"))
        else:
            self.video_quality_lab.SetLabel(get_mapping_key_by_value(video_quality_map, self.task_info.video_quality_id, "--"))
            self.video_codec_lab.SetLabel(get_mapping_key_by_value(video_codec_map, self.task_info.video_codec_id, "--"))
        
        if self.task_info.progress == 100:
            self.video_size_lab.SetLabel(FormatTool.format_size(self.task_info.total_file_size))
        else:
            self.video_size_lab.SetLabel(f"{FormatTool.format_size(self.task_info.total_downloaded_size)}/{FormatTool.format_size(self.task_info.total_file_size)}")
    
    def show_cover(self):
        def is_16_9(image: wx.Image):
            width, height = image.GetSize()

            return (width / height) == (16 / 9)

        def crop(image: wx.Image):
            # 将非 16:9 封面调整为 16:9
                width, height = image.GetSize()

                new_height = int(width * (9 / 16))

                y_offset = (height - new_height) // 2

                if y_offset >= 0:
                    return image.GetSubImage(wx.Rect(0, y_offset, width, new_height))
                else:
                    new_width = int(height * (16 / 9))
                    x_offset = (width - new_width) // 2
                    return image.GetSubImage(wx.Rect(x_offset, 0, new_width, height))

        def get_bitmap():
            cache = DataCache.get_cache(self.task_info.cover_url)

            if cache:
                return cache
            else:
                content = RequestTool.request_get(self.task_info.cover_url).content

                DataCache.set_cache(self.task_info.cover_url, content)

                return content

        def setBitmap(image: wx.Image):
            if not self._destroy:
                self.cover_bmp.SetBitmap(image.ConvertToBitmap())

        if not self._show_cover:
            self._show_cover = True
            size = self.FromDIP((112, 63))

            self._cover = get_bitmap()

            image = wx.Image(BytesIO(self._cover))

            if not is_16_9(image):
                image = crop(image)

            image: wx.Image = image.Scale(size[0], size[1], wx.IMAGE_QUALITY_HIGH)

            wx.CallAfter(setBitmap, image)

    def onDestroyEVT(self, event):
        self._destroy = True

        event.Skip()

    def onViewCoverEVT(self, event):
        dlg = CoverViewerDialog(self.download_window, self._cover)
        dlg.Show()

    def onPauseEVT(self, event):
        match DownloadStatus(self.task_info.status):
            case DownloadStatus.Waiting:
                self.start_download()

            case DownloadStatus.Downloading:
                self.pause_download()

            case DownloadStatus.Pause:
                self.resume_download()

            case DownloadStatus.Complete:
                self.open_file_location()

    def onStopEVT(self, event):
        self.destroy_panel(event)

        self.file_tool.delete_file()

        if hasattr(self, "downloader"):
            self.downloader.stop_download()
    
    def destroy_panel(self, event = None):
        self.Hide()
        self.Destroy()
        
        if event:
            self.callback.onUpdateCountTitleCallback()

    def start_download(self):
        def get_downloader_callback():
            downloader_callback = DownloaderCallback()
            downloader_callback.onStartDownloadCallback = self.onStartDownload
            downloader_callback.onDownloadingCallback = self.onDownloading
            downloader_callback.onDownloadFinish = self.onDownloadFinish
            downloader_callback.onErrorCallback = self.onDownloadError

            return downloader_callback

        def worker():
            # 获取下载链接
            download_parser = DownloadParser(self.task_info)
            downloader_info = download_parser.get_download_url()

            self.file_tool.update_info("task_info", self.task_info.to_dict())

            # 开始下载
            self.downloader.set_downloader_info(downloader_info)

            self.downloader.start_download()

        self.set_download_status(DownloadStatus.Downloading.value)

        self.downloader = Downloader(self.task_info, self.file_tool, get_downloader_callback())

        Thread(target = worker).start()

    def pause_download(self):
        self.set_download_status(DownloadStatus.Pause.value)

        self.downloader.stop_download()

    def resume_download(self):
        if self.task_info.status != DownloadStatus.Downloading.value:
            if self.task_info.progress == 100:
                self.onDownloadFinish()
            else:
                self.start_download()

    def merge_video(self):
        def get_callback():
            callback = MergeCallback()
            callback.onSuccess = self.onMergeSuccess
            callback.onError = self.onMergeError
            return callback

        self.ffmpeg = FFmpeg()
        self.ffmpeg.set_task_info(self.task_info)

        self.ffmpeg.merge_video(self.full_file_name, get_callback())

    def open_file_location(self):
        path = os.path.join(Config.Download.path, self.full_file_name)

        FileDirectoryTool.open_file_location(path)

    def onStartDownload(self):
        def worker():
            self.show_task_info()

            self.Layout()

        wx.CallAfter(worker)

    def onDownloading(self, speed: str):
        def worker():
            if not self._destroy:
                self.progress_bar.SetValue(self.task_info.progress)
                self.progress_bar.SetToolTip(f"{self.task_info.progress}%")

                self.speed_lab.SetLabel(speed)
                self.video_size_lab.SetLabel(f"{FormatTool.format_size(self.task_info.total_downloaded_size)}/{FormatTool.format_size(self.task_info.total_file_size)}")

                self.Layout()

        wx.CallAfter(worker)

    def onDownloadFinish(self):
        def worker():
            if self.task_info.ffmpeg_merge:
                self.set_download_status(DownloadStatus.Merging.value)

                self.video_size_lab.SetLabel(FormatTool.format_size(self.task_info.total_file_size))

                self.Layout()

                Thread(target = self.merge_video).start()
            else:
                pass

        wx.CallAfter(worker)

    def onMergeSuccess(self):
        def worker():
            self.set_download_status(DownloadStatus.Complete.value)

            self.destroy_panel(1)

            self.ffmpeg.clear_temp_files()

            self.callback.onAddPanelCallback(self.task_info)

        wx.CallAfter(worker)

    def onMergeError(self):
        def worker():


            self.set_download_error(DownloadStatus.MergeError.value)
        
        wx.CallAfter(worker)

    def onDownloadError(self):
        def worker():

            
            self.set_download_error(DownloadStatus.DownloadError.value)

        wx.CallAfter(worker)

    def set_download_error(self, status: int):
        self.set_download_status(status)

    def set_download_status(self, status: int):
        def set_button_icon(status: int):
            match DownloadStatus(status):
                case DownloadStatus.Downloading:
                    self.pause_btn.SetBitmap(self.icon_manager.get_icon_bitmap(IconType.PAUSE_ICON))

                    self.pause_btn.SetToolTip("暂停下载")
                    self.speed_lab.SetLabel("正在获取下载链接...")

                case DownloadStatus.Pause:
                    self.pause_btn.SetBitmap(self.icon_manager.get_icon_bitmap(IconType.RESUME_ICON))

                    self.pause_btn.SetToolTip("继续下载")
                    self.speed_lab.SetLabel("暂停中")

                case DownloadStatus.Merging:
                    self.pause_btn.SetBitmap(self.icon_manager.get_icon_bitmap(IconType.PAUSE_ICON))

                    if self.task_info.download_option == DownloadOption.OnlyAudio.value:
                        lab = "正在转换音频..."
                    else:
                        lab = "正在合成视频..."

                    self.pause_btn.SetToolTip(lab)
                    self.speed_lab.SetLabel(lab)

                    self.pause_btn.Enable(False)
                    self.stop_btn.Enable(False)

                case DownloadStatus.Complete:
                    self.pause_btn.SetBitmap(self.icon_manager.get_icon_bitmap(IconType.FOLDER_ICON))

                    self.pause_btn.SetToolTip("打开文件所在位置")
                    self.speed_lab.SetLabel("下载完成")

                case DownloadStatus.MergeError:
                    self.pause_btn.SetBitmap(self.icon_manager.get_icon_bitmap(IconType.RETRY_ICON))

                    self.pause_btn.SetToolTip("重试")
                    self.pause_btn.Enable(True)
                    self.stop_btn.Enable(True)
                    self.speed_lab.SetForegroundColour("red")

                    if self.task_info.download_option == DownloadOption.OnlyAudio.value:
                        lab = "转换音频"
                    else:
                        lab = "合成视频"

                    if hasattr(self, "error_info"):
                        self.speed_lab.SetLabel(f"{lab}失败，点击查看详情")
                        self.speed_lab.SetCursor(wx.Cursor(wx.Cursor(wx.CURSOR_HAND)))
                    else:
                        self.speed_lab.SetLabel(f"{lab}失败")

                case DownloadStatus.DownloadError:
                    self.pause_btn.SetBitmap(self.icon_manager.get_icon_bitmap(IconType.RETRY_ICON))

                    self.pause_btn.SetToolTip("重试")
                    self.speed_lab.SetForegroundColour("red")

                    if hasattr(self, "error_info"):
                        self.speed_lab.SetLabel("下载失败，点击查看详情")
                        self.speed_lab.SetCursor(wx.Cursor(wx.Cursor(wx.CURSOR_HAND)))
                    else:
                        self.speed_lab.SetLabel("下载失败")
        
        self.task_info.status = status

        set_button_icon(status)

        kwargs = {
            "status": status
        }

        self.file_tool.update_task_info_kwargs(**kwargs)
    
    @property
    def full_file_name(self):
        file_name = FormatTool.format_title_template(Config.Advanced.file_name_template, self.task_info)

        return f"{file_name}.{self.task_info.output_type}"
