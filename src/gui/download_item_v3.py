import wx
from io import BytesIO

from utils.common.icon_v2 import IconManager, IconType
from utils.common.data_type import DownloadTaskInfo, TaskPanelCallback
from utils.common.enums import DownloadOption
from utils.common.map import video_quality_map, audio_quality_map, video_codec_map, get_mapping_key_by_value
from utils.tool_v2 import FormatTool, DownloadFileTool, RequestTool

from gui.templates import InfoLabel

class EmptyItemPanel(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        self.init_UI()

    def init_UI(self):
        self.empty_lab = wx.StaticText(self, -1, "无项目")

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.AddStretchSpacer()
        hbox.Add(self.empty_lab, 0, wx.ALL, 10)
        hbox.AddStretchSpacer()

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.AddStretchSpacer(200)
        vbox.Add(hbox, 0, wx.EXPAND)
        vbox.AddStretchSpacer(200)

        self.SetSizer(vbox)

class DownloadTaskItemPanel(wx.Panel):
    def __init__(self, parent, info: DownloadTaskInfo, callback: TaskPanelCallback):
        self.task_info, self.callback = info, callback

        wx.Panel.__init__(self, parent, -1)

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

    def init_UI(self):
        self.icon_manager = IconManager(self)

        self.cover_bmp = wx.StaticBitmap(self, -1, size = self.FromDIP((112, 63)))

        self.title_lab = wx.StaticText(self, -1, size = self.FromDIP((300, 24)), style = wx.ST_ELLIPSIZE_MIDDLE)

        self.video_quality_lab = InfoLabel(self, "--", size = self.FromDIP((-1, -1)))
        self.video_codec_lab = InfoLabel(self, "--", size = self.FromDIP((-1, -1)))
        self.video_size_lab = InfoLabel(self, "--", size = self.FromDIP((-1, -1)))

        video_info_hbox = wx.BoxSizer(wx.HORIZONTAL)

        video_info_hbox.Add(self.video_quality_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, 10)
        video_info_hbox.AddSpacer(20)
        video_info_hbox.Add(self.video_codec_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, 10)
        video_info_hbox.AddSpacer(20)
        video_info_hbox.Add(self.video_size_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, 10)

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
        self.stop_btn.Bind(wx.EVT_BUTTON, self.onStopEVT)

    def init_utils(self):
        self._show_cover = False

        self.show_task_info()

        self.file_tool = DownloadFileTool(self.task_info.id)

    def show_task_info(self):
        self.title_lab.SetLabel(self.task_info.title)
        self.progress_bar.SetValue(self.task_info.progress)

        if self.task_info.download_option == DownloadOption.OnlyAudio.value:
            self.video_quality_lab.SetLabel("音频")
            self.video_codec_lab.SetLabel(get_mapping_key_by_value(audio_quality_map, self.task_info.audio_quality_id, "--"))
        else:
            self.video_quality_lab.SetLabel(get_mapping_key_by_value(video_quality_map, self.task_info.video_quality_id, "--"))
            self.video_codec_lab.SetLabel(get_mapping_key_by_value(video_codec_map, self.task_info.video_codec_id, "--"))
        
        if self.task_info.progress == 100:
            self.video_size_lab.SetLabel(FormatTool.format_size(self.task_info.total_size))
        else:
            self.video_size_lab.SetLabel(f"{FormatTool.format_size(self.task_info.completed_size)}/{FormatTool.format_size(self.task_info.total_size)}")
    
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

        def setBitmap(image: wx.Image):
            self.cover_bmp.SetBitmap(image.ConvertToBitmap())

        if not self._show_cover:
            self._show_cover = True
            size = self.FromDIP((112, 63))

            self._cover = RequestTool.request_get(self.task_info.cover_url).content

            image = wx.Image(BytesIO(self._cover))

            if not is_16_9(image):
                image = crop(image)

            image: wx.Image = image.Scale(size[0], size[1], wx.IMAGE_QUALITY_HIGH)

            wx.CallAfter(setBitmap, image)

    def onStopEVT(self, event):
        self.Hide()
        self.Destroy()

        self.file_tool.delete_file()

        if event:
            self.callback.onUpdateCountTitleCallback()