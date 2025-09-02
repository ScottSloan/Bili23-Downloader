import wx

from utils.config import Config

from gui.component.panel.panel import Panel
from gui.component.misc.tooltip import ToolTip

class MediaOptionStaticBox(Panel):
    def __init__(self, parent: wx.Window):
        from gui.dialog.download_option.download_option_dialog import DownloadOptionDialog

        self.parent: DownloadOptionDialog = parent

        Panel.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

    def init_UI(self):
        media_box = wx.StaticBox(self, -1, "媒体下载选项")

        self.download_video_steam_chk = wx.CheckBox(media_box, -1, "视频流")
        self.video_stream_tip = ToolTip(media_box)
        self.video_stream_tip.set_tooltip('下载独立的视频流文件\n\n视频和音频分开存储，需要合并为一个完整的视频文件')

        video_stream_hbox = wx.BoxSizer(wx.HORIZONTAL)
        video_stream_hbox.Add(self.download_video_steam_chk, 0, wx.ALL & (~wx.RIGHT) | wx.ALIGN_CENTER, self.FromDIP(6))
        video_stream_hbox.Add(self.video_stream_tip, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.download_audio_steam_chk = wx.CheckBox(media_box, -1, "音频流")
        self.audio_stream_tip = ToolTip(media_box)
        self.audio_stream_tip.set_tooltip('下载独立的音频流文件')

        audio_stream_hbox = wx.BoxSizer(wx.HORIZONTAL)
        audio_stream_hbox.Add(self.download_audio_steam_chk, 0, wx.ALL & (~wx.RIGHT) | wx.ALIGN_CENTER, self.FromDIP(6))
        audio_stream_hbox.Add(self.audio_stream_tip, 0, wx.ALL & (~wx.LEFT)| wx.ALIGN_CENTER, self.FromDIP(6))
        
        self.ffmpeg_merge_chk = wx.CheckBox(media_box, -1, "合并视频和音频")
        ffmpeg_merge_tip = ToolTip(media_box)
        ffmpeg_merge_tip.set_tooltip("选中后，在下载完成时，程序会自动将独立的视频和音频文件合并为一个完整的视频文件")

        ffmpeg_merge_hbox = wx.BoxSizer(wx.HORIZONTAL)
        ffmpeg_merge_hbox.Add(self.ffmpeg_merge_chk, 0, wx.ALL & (~wx.RIGHT) & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
        ffmpeg_merge_hbox.Add(ffmpeg_merge_tip, 0, wx.ALL & (~wx.LEFT) & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.keep_original_files_chk = wx.CheckBox(media_box, -1, "合并完成后保留原始文件")
        keep_original_files_tip = ToolTip(media_box)
        keep_original_files_tip.set_tooltip("合并完成后，保留原始的视频和音频文件")

        keep_original_files_hbox = wx.BoxSizer(wx.HORIZONTAL)
        keep_original_files_hbox.Add(self.keep_original_files_chk, 0, wx.ALL & (~wx.RIGHT) & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
        keep_original_files_hbox.Add(keep_original_files_tip, 0, wx.ALL & (~wx.LEFT) & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))

        media_flex_grid_box = wx.FlexGridSizer(2, 2, 0, 0)
        media_flex_grid_box.Add(video_stream_hbox, 0, wx.EXPAND)
        media_flex_grid_box.Add(audio_stream_hbox, 0, wx.EXPAND)
        media_flex_grid_box.Add(ffmpeg_merge_hbox, 0, wx.EXPAND)
        media_flex_grid_box.Add(keep_original_files_hbox, 0, wx.EXPAND)

        media_sbox = wx.StaticBoxSizer(media_box, wx.VERTICAL)
        media_sbox.Add(media_flex_grid_box, 0, wx.EXPAND)

        self.SetSizer(media_sbox)

    def Bind_EVT(self):
        self.download_video_steam_chk.Bind(wx.EVT_CHECKBOX, self.onChangeStreamDownloadOptionEVT)
        self.download_audio_steam_chk.Bind(wx.EVT_CHECKBOX, self.onChangeStreamDownloadOptionEVT)

        self.ffmpeg_merge_chk.Bind(wx.EVT_CHECKBOX, self.onEnableKeepFilesEVT)

    def load_data(self):
        self.download_video_steam_chk.SetValue("video" in Config.Download.stream_download_option)
        self.download_audio_steam_chk.SetValue("audio" in Config.Download.stream_download_option)

        self.keep_original_files_chk.SetValue(Config.Merge.keep_original_files)

        self.onChangeStreamDownloadOptionEVT(0)

    def save(self):
        Config.Download.stream_download_option.clear()

        if self.download_video_steam_chk.GetValue():
            Config.Download.stream_download_option.append("video")
        
        if self.download_audio_steam_chk.GetValue():
            Config.Download.stream_download_option.append("audio")

        Config.Merge.keep_original_files = self.keep_original_files_chk.GetValue()

    def onChangeStreamDownloadOptionEVT(self, event):
        video_enable = self.download_video_steam_chk.GetValue()
        audio_enable = self.download_audio_steam_chk.GetValue()

        self.parent.media_info_box.enable_video_quality_group(video_enable)
        self.parent.media_info_box.enable_audio_quality_group(audio_enable)

        ffmpeg_merge_enable = video_enable and audio_enable

        self.ffmpeg_merge_chk.Enable(ffmpeg_merge_enable)
        self.ffmpeg_merge_chk.SetValue(ffmpeg_merge_enable)

        self.onEnableKeepFilesEVT(0)

    def onEnableKeepFilesEVT(self, event):
        enable = self.ffmpeg_merge_chk.GetValue()

        self.keep_original_files_chk.Enable(enable)
    
    def enable_audio_download_option(self, enable: bool):
        self.download_audio_steam_chk.Enable(enable)
        self.download_audio_steam_chk.SetValue(enable)

        self.onChangeStreamDownloadOptionEVT(0)
