import wx
import os
import re
import time
import requests
from requests.auth import HTTPProxyAuth
from gui.templates import ScrolledPanel

from gui.dialog.ffmpeg import DetectDialog

from utils.config import Config, ConfigUtils
from utils.tool_v2 import RequestTool, DownloadFileTool
from utils.common.thread import Thread
from utils.common.map import video_quality_mapping, audio_quality_mapping, video_codec_mapping, danmaku_format_mapping, subtitle_format_mapping, cdn_mapping, get_mapping_index_by_value
from utils.icon_v2 import IconManager, IconType

class SettingWindow(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, "设置")

        self.init_UI()

        self.Bind_EVT()

        self.CenterOnParent()

    def init_UI(self):
        def _get_scale_size(_size: tuple):
            match Config.Sys.platform:
                case "windows":
                    return self.FromDIP(_size)
                
                case "linux" | "darwin":
                    return wx.DefaultSize

        self.note = wx.Notebook(self, -1)

        self.note.AddPage(DownloadTab(self.note, self.GetParent()), "下载")
        self.note.AddPage(MergeTab(self.note, self.GetParent()), "合成")
        self.note.AddPage(ExtraTab(self.note, self.GetParent()), "附加内容")
        self.note.AddPage(ProxyTab(self.note, self.GetParent()), "代理")
        self.note.AddPage(MiscTab(self.note, self.GetParent()), "其他")

        self.ok_btn = wx.Button(self, wx.ID_OK, "确定", size = _get_scale_size((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, "取消", size = _get_scale_size((80, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer(1)
        bottom_hbox.Add(self.ok_btn, 0, wx.ALL & (~wx.TOP), 10)
        bottom_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), 10)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.note, 0, wx.EXPAND | wx.ALL, 10)
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)
    
    def Bind_EVT(self):
        self.ok_btn.Bind(wx.EVT_BUTTON, self.onConfirm)
    
    def onConfirm(self, event):
        for i in range(0, self.note.GetPageCount()):
            if not self.note.GetPage(i).onConfirm():
                return
            
        event.Skip()

class DownloadTab(wx.Panel):
    def __init__(self, parent, _main_window):
        self._main_window = _main_window

        wx.Panel.__init__(self, parent, -1)

        self.init_UI()

        self.Bind_EVT()

        self.init_data()

    def init_UI(self):
        def _get_scale_size(_size: tuple):
            match Config.Sys.platform:
                case "windows":
                    return self.FromDIP(_size)
                
                case "linux" | "darwin":
                    return wx.DefaultSize
        
        def _get_panel_size():
            match Config.Sys.platform:
                case "windows":
                    return self.FromDIP((-1, 350))
                
                case "linux" | "darwin":
                    return self.FromDIP((400, 430))

        def _layout():
            self.scrolled_panel.Layout()

            self.scrolled_panel.sizer.Layout()

            self.scrolled_panel.SetupScrolling(scroll_x = False, scrollToTop = False)

        icon_manager = IconManager(self.GetDPIScaleFactor())

        self.download_box = wx.StaticBox(self, -1, "下载设置")

        self.scrolled_panel = ScrolledPanel(self.download_box, _get_panel_size())

        path_lab = wx.StaticText(self.scrolled_panel, -1, "下载目录")
        self.path_box = wx.TextCtrl(self.scrolled_panel, -1, size = _get_scale_size((220, 24)))
        self.browse_btn = wx.Button(self.scrolled_panel, -1, "浏览", size = _get_scale_size((60, 24)))

        path_hbox = wx.BoxSizer(wx.HORIZONTAL)
        path_hbox.Add(self.path_box, 1, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, 10)
        path_hbox.Add(self.browse_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.ALIGN_CENTER, 10)
        
        self.max_thread_lab = wx.StaticText(self.scrolled_panel, -1, "多线程数：1")
        self.max_thread_slider = wx.Slider(self.scrolled_panel, -1, 1, 1, 8)

        self.max_download_lab = wx.StaticText(self.scrolled_panel, -1, "并行下载数：1")
        self.max_download_slider = wx.Slider(self.scrolled_panel, -1, 1, 1, 8)

        video_lab = wx.StaticText(self.scrolled_panel, -1, "默认下载清晰度")
        self.video_quality_choice = wx.Choice(self.scrolled_panel, -1, choices = list(video_quality_mapping.keys()))
        self.video_quality_tip = wx.StaticBitmap(self.scrolled_panel, -1, icon_manager.get_icon_bitmap(IconType.INFO_ICON))
        self.video_quality_tip.SetCursor(wx.Cursor(wx.CURSOR_HAND))
        self.video_quality_tip.SetToolTip("说明")

        video_quality_hbox = wx.BoxSizer(wx.HORIZONTAL)
        video_quality_hbox.Add(video_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        video_quality_hbox.Add(self.video_quality_choice, 0, wx.ALL, 10)
        video_quality_hbox.Add(self.video_quality_tip, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, 10)

        audio_lab = wx.StaticText(self.scrolled_panel, -1, "默认下载音质")
        self.audio_quality_choice = wx.Choice(self.scrolled_panel, -1, choices = list(audio_quality_mapping.keys()))
        self.audio_quality_tip = wx.StaticBitmap(self.scrolled_panel, -1, icon_manager.get_icon_bitmap(IconType.INFO_ICON))
        self.audio_quality_tip.SetCursor(wx.Cursor(wx.CURSOR_HAND))
        self.audio_quality_tip.SetToolTip("说明")

        sound_quality_hbox = wx.BoxSizer(wx.HORIZONTAL)
        sound_quality_hbox.Add(audio_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        sound_quality_hbox.Add(self.audio_quality_choice, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        sound_quality_hbox.Add(self.audio_quality_tip, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, 10)

        codec_lab = wx.StaticText(self.scrolled_panel, -1, "视频编码格式")
        self.codec_choice = wx.Choice(self.scrolled_panel, -1, choices = ["AVC/H.264", "HEVC/H.265", "AV1"])
        self.codec_tip = wx.StaticBitmap(self.scrolled_panel, -1, icon_manager.get_icon_bitmap(IconType.INFO_ICON))
        self.codec_tip.SetCursor(wx.Cursor(wx.CURSOR_HAND))
        self.codec_tip.SetToolTip("说明")

        codec_hbox = wx.BoxSizer(wx.HORIZONTAL)
        codec_hbox.Add(codec_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        codec_hbox.Add(self.codec_choice, 0, wx.ALL, 10)
        codec_hbox.Add(self.codec_tip, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, 10)

        self.enable_dolby_chk = wx.CheckBox(self.scrolled_panel, -1, '自动下载杜比视界或杜比全景声')
        self.dolby_tip = wx.StaticBitmap(self.scrolled_panel, -1, icon_manager.get_icon_bitmap(IconType.INFO_ICON))
        self.dolby_tip.SetCursor(wx.Cursor(wx.CURSOR_HAND))
        self.dolby_tip.SetToolTip("说明")

        dolby_hbox = wx.BoxSizer(wx.HORIZONTAL)
        dolby_hbox.Add(self.enable_dolby_chk, 0, wx.ALL, 10)
        dolby_hbox.Add(self.dolby_tip, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, 10)

        self.speed_limit_chk = wx.CheckBox(self.scrolled_panel, -1, "对单个下载任务进行限速")
        self.speed_limit_lab = wx.StaticText(self.scrolled_panel, -1, "最高")
        self.speed_limit_box = wx.TextCtrl(self.scrolled_panel, -1, size = self.FromDIP((50, 25)))
        self.speed_limit_unit_lab = wx.StaticText(self.scrolled_panel, -1, "MB/s")

        speed_limit_hbox = wx.BoxSizer(wx.HORIZONTAL)
        speed_limit_hbox.AddSpacer(30)
        speed_limit_hbox.Add(self.speed_limit_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        speed_limit_hbox.Add(self.speed_limit_box, 0, wx.ALL & (~wx.LEFT), 10)
        speed_limit_hbox.Add(self.speed_limit_unit_lab, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, 10)

        self.enable_custom_cdn_chk = wx.CheckBox(self.scrolled_panel, -1, "替换音视频流 CDN")
        self.custom_cdn_auto_switch_radio = wx.RadioButton(self.scrolled_panel, -1, "自动切换")
        self.custom_cdn_manual_radio = wx.RadioButton(self.scrolled_panel, -1, "手动设置")

        custom_cdn_mode_hbox = wx.BoxSizer(wx.HORIZONTAL)
        custom_cdn_mode_hbox.AddSpacer(30)
        custom_cdn_mode_hbox.Add(self.custom_cdn_auto_switch_radio, 0, wx.ALL & (~wx.BOTTOM) | wx.ALIGN_CENTER, 10)
        custom_cdn_mode_hbox.Add(self.custom_cdn_manual_radio, 0, wx.ALL & (~wx.LEFT) & (~wx.BOTTOM) | wx.ALIGN_CENTER, 10)

        self.custom_cdn_lab = wx.StaticText(self.scrolled_panel, -1, "CDN")
        self.custom_cdn_box = wx.ComboBox(self.scrolled_panel, -1, choices = list(cdn_mapping.values()))

        custom_cdn_hbox = wx.BoxSizer(wx.HORIZONTAL)
        custom_cdn_hbox.AddSpacer(30)
        custom_cdn_hbox.Add(self.custom_cdn_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        custom_cdn_hbox.Add(self.custom_cdn_box, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, 10)

        self.add_number_chk = wx.CheckBox(self.scrolled_panel, -1, "批量下载视频时自动添加序号")
        self.delete_history_chk = wx.CheckBox(self.scrolled_panel, -1, "下载完成后清除本地下载记录")
        self.show_toast_chk = wx.CheckBox(self.scrolled_panel, -1, "允许弹出通知提示")

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(path_lab, 0, wx.ALL, 10)
        vbox.Add(path_hbox, 0, wx.EXPAND)
        vbox.Add(self.max_thread_lab, 0, wx.ALL & (~wx.TOP), 10)
        vbox.Add(self.max_thread_slider, 0, wx.EXPAND | wx.ALL & (~wx.TOP), 10)
        vbox.Add(self.max_download_lab, 0, wx.ALL & (~wx.TOP), 10)
        vbox.Add(self.max_download_slider, 0, wx.EXPAND | wx.ALL & (~wx.TOP), 10)
        vbox.Add(video_quality_hbox, 0, wx.EXPAND)
        vbox.Add(sound_quality_hbox, 0, wx.EXPAND)
        vbox.Add(codec_hbox, 0, wx.EXPAND)
        vbox.Add(dolby_hbox, 0, wx.EXPAND)
        vbox.Add(self.speed_limit_chk, 0, wx.ALL & (~wx.BOTTOM), 10)
        vbox.Add(speed_limit_hbox, 0, wx.EXPAND)
        vbox.Add(self.enable_custom_cdn_chk, 0, wx.ALL & (~wx.BOTTOM) & (~wx.TOP), 10)
        vbox.Add(custom_cdn_mode_hbox, 0, wx.EXPAND)
        vbox.Add(custom_cdn_hbox, 0, wx.EXPAND)
        vbox.Add(self.add_number_chk, 0, wx.ALL & (~wx.TOP), 10)
        vbox.Add(self.delete_history_chk, 0, wx.ALL, 10)
        vbox.Add(self.show_toast_chk, 0, wx.ALL, 10)

        self.scrolled_panel.sizer.Add(vbox, 0, wx.EXPAND)

        download_sbox = wx.StaticBoxSizer(self.download_box)
        download_sbox.Add(self.scrolled_panel, 0, wx.EXPAND)

        download_vbox = wx.BoxSizer(wx.VERTICAL)
        download_vbox.Add(download_sbox, 0, wx.ALL | wx.EXPAND, 10)

        self.SetSizerAndFit(download_vbox)

        _layout()

    def Bind_EVT(self):
        self.browse_btn.Bind(wx.EVT_BUTTON, self.onBrowsePathEVT)

        self.max_thread_slider.Bind(wx.EVT_SLIDER, self.onThreadCountSlideEVT)
        self.max_download_slider.Bind(wx.EVT_SLIDER, self.onDownloadCountSlideEVT)

        self.speed_limit_chk.Bind(wx.EVT_CHECKBOX, self.onChangeSpeedLimitEVT)
        self.enable_custom_cdn_chk.Bind(wx.EVT_CHECKBOX, self.onChangeCustomCDNEVT)
        self.custom_cdn_auto_switch_radio.Bind(wx.EVT_RADIOBUTTON, self.onChangeCustomCDNModeEVT)
        self.custom_cdn_manual_radio.Bind(wx.EVT_RADIOBUTTON, self.onChangeCustomCDNModeEVT)

        self.video_quality_tip.Bind(wx.EVT_LEFT_UP, self.onVideoQualityTipEVT)
        self.audio_quality_tip.Bind(wx.EVT_LEFT_UP, self.onAudioQualityTipEVT)
        self.codec_tip.Bind(wx.EVT_LEFT_UP, self.onVideoCodecTipEVT)
        self.dolby_tip.Bind(wx.EVT_LEFT_UP, self.onDolbyTipEVT)

    def init_data(self):
        self.path_box.SetValue(Config.Download.path)
        
        self.max_thread_lab.SetLabel("多线程数：{}".format(Config.Download.max_thread_count))
        self.max_thread_slider.SetValue(Config.Download.max_thread_count)

        self.max_download_lab.SetLabel("并行下载数：{}".format(Config.Download.max_download_count))
        self.max_download_slider.SetValue(Config.Download.max_download_count)
        
        self.video_quality_choice.SetSelection(get_mapping_index_by_value(video_quality_mapping, Config.Download.video_quality_id))
        self.audio_quality_choice.SetSelection(get_mapping_index_by_value(audio_quality_mapping, Config.Download.audio_quality_id))

        self.codec_choice.SetSelection(get_mapping_index_by_value(video_codec_mapping, Config.Download.video_codec_id))

        self.enable_dolby_chk.SetValue(Config.Download.enable_dolby)
        self.speed_limit_chk.SetValue(Config.Download.enable_speed_limit)
        self.enable_custom_cdn_chk.SetValue(Config.Download.enable_custom_cdn)
        self.add_number_chk.SetValue(Config.Download.add_number)
        self.delete_history_chk.SetValue(Config.Download.delete_history)
        self.show_toast_chk.SetValue(Config.Download.enable_notification)

        self.speed_limit_box.SetValue(str(Config.Download.speed_limit_in_mb))
        self.custom_cdn_box.SetValue(Config.Download.custom_cdn)

        match Config.Download.custom_cdn_mode:
            case Config.Type.CUSTOM_CDN_MODE_AUTO:
                self.custom_cdn_auto_switch_radio.SetValue(True)

            case Config.Type.CUSTOM_CDN_MODE_MANUAL:
                self.custom_cdn_manual_radio.SetValue(True)

        self.onChangeSpeedLimitEVT(0)
        self.onChangeCustomCDNEVT(0)

    def save(self):
        def _update_download_window():
            self._main_window.download_window.max_download_choice.SetSelection(Config.Download.max_download_count - 1)

            self._main_window.download_window.onChangeMaxDownloaderEVT(None)

        Config.Download.path = self.path_box.GetValue()
        Config.Download.max_thread_count = self.max_thread_slider.GetValue()
        Config.Download.max_download_count = self.max_download_slider.GetValue()
        Config.Download.video_quality_id = video_quality_mapping[self.video_quality_choice.GetStringSelection()]
        Config.Download.audio_quality_id = audio_quality_mapping[self.audio_quality_choice.GetStringSelection()]
        Config.Download.video_codec_id = video_codec_mapping[self.codec_choice.GetStringSelection()]
        Config.Download.enable_dolby = self.enable_dolby_chk.GetValue()
        Config.Download.add_number = self.add_number_chk.GetValue()
        Config.Download.delete_history = self.delete_history_chk.GetValue()
        Config.Download.enable_notification = self.show_toast_chk.GetValue()
        Config.Download.enable_speed_limit = self.speed_limit_chk.GetValue()
        Config.Download.speed_limit_in_mb = int(self.speed_limit_box.GetValue())
        Config.Download.enable_custom_cdn = self.enable_custom_cdn_chk.GetValue()
        Config.Download.custom_cdn = self.custom_cdn_box.GetValue()

        if self.custom_cdn_auto_switch_radio.GetValue():
            Config.Download.custom_cdn_mode = 0
        else:
            Config.Download.custom_cdn_mode = 1

        kwargs = {
            "path": Config.Download.path,
            "max_download_count": Config.Download.max_download_count,
            "max_thread_count": Config.Download.max_thread_count,
            "video_quality_id": Config.Download.video_quality_id,
            "audio_quality_id": Config.Download.audio_quality_id,
            "video_codec_id": Config.Download.video_codec_id,
            "enable_dolby": Config.Download.enable_dolby,
            "enable_notification": Config.Download.enable_notification,
            "delete_history": Config.Download.delete_history,
            "add_number": Config.Download.add_number,
            "enable_speed_limit": Config.Download.enable_speed_limit,
            "speed_limit_in_mb": Config.Download.speed_limit_in_mb,
            "enable_custom_cdn": Config.Download.enable_custom_cdn,
            "custom_cdn": Config.Download.custom_cdn,
            "custom_cdn_mode": Config.Download.custom_cdn_mode
        }

        utils = ConfigUtils()
        utils.update_config_kwargs(Config.APP.app_config_path, "download", **kwargs)

        # 更新下载窗口中并行下载数信息
        _update_download_window()
        
    def onConfirm(self):
        if not self.isValidSpeedLimit(self.speed_limit_box.GetValue()):
            wx.MessageDialog(self, "速度值无效\n\n输入的速度值无效，应为一个正整数", "警告", wx.ICON_WARNING).ShowModal()
            return False
        
        self.save()

        return True
    
    def onBrowsePathEVT(self, event):
        dlg = wx.DirDialog(self, "选择下载目录", defaultPath = Config.Download.path)

        if dlg.ShowModal() == wx.ID_OK:
            save_path = dlg.GetPath()
            self.path_box.SetValue(save_path)

        dlg.Destroy()

    def onThreadCountSlideEVT(self, event):
        self.max_thread_lab.SetLabel("多线程数：{}".format(self.max_thread_slider.GetValue()))

    def onDownloadCountSlideEVT(self, event):
        self.max_download_lab.SetLabel("并行下载数：{}".format(self.max_download_slider.GetValue()))

    def onChangeSpeedLimitEVT(self, event):
        self.speed_limit_box.Enable(self.speed_limit_chk.GetValue())
        self.speed_limit_lab.Enable(self.speed_limit_chk.GetValue())
        self.speed_limit_unit_lab.Enable(self.speed_limit_chk.GetValue())
        
    def onChangeCustomCDNEVT(self, event):
        self.custom_cdn_auto_switch_radio.Enable(self.enable_custom_cdn_chk.GetValue())
        self.custom_cdn_manual_radio.Enable(self.enable_custom_cdn_chk.GetValue())

        if self.enable_custom_cdn_chk.GetValue():
            self.onChangeCustomCDNModeEVT(0)
        else:
            self.custom_cdn_lab.Enable(False)
            self.custom_cdn_box.Enable(False)

    def onChangeCustomCDNModeEVT(self, event):
        self.custom_cdn_lab.Enable(self.custom_cdn_manual_radio.GetValue())
        self.custom_cdn_box.Enable(self.custom_cdn_manual_radio.GetValue())

    def isValidSpeedLimit(self, speed):
        return bool(re.fullmatch(r'[1-9]\d*', speed))
    
    def onVideoQualityTipEVT(self, event):
        wx.MessageDialog(self, "默认下载清晰度选项说明\n\n指定下载视频的清晰度，取决于视频的支持情况；若视频无所选的清晰度，则自动下载最高可用的清晰度\n\n自动：自动下载每个视频的最高可用的清晰度\n\n若需要自动下载杜比视频，请开启下方的选项", "说明", wx.ICON_INFORMATION).ShowModal()

    def onAudioQualityTipEVT(self, event):
        wx.MessageDialog(self, "默认下载音质选项说明\n\n指定下载视频的音质，取决于视频的支持情况；若视频无所选的音质，则自动下载最高可用的音质\n\n自动：自动下载每个视频的最高可用音质", "说明", wx.ICON_INFORMATION).ShowModal()

    def onVideoCodecTipEVT(self, event):
        wx.MessageDialog(self, "视频编码格式选项说明\n\n指定下载视频的编码格式，取决于视频的支持情况；若视频无所选的编码格式，则默认下载 AVC/H.264", "说明", wx.ICON_INFORMATION).ShowModal()
    
    def onDolbyTipEVT(self, event):
        wx.MessageDialog(self, '自动下载杜比选项说明\n\n当上方选择 "自动" 时，若视频支持杜比，则自动下载杜比视界或杜比全景声，否则需要手动选择\n\n开启此项前请先确认设备是否支持杜比', "说明", wx.ICON_INFORMATION).ShowModal()

class MergeTab(wx.Panel):
    def __init__(self, parent, _main_window):
        self._main_window = _main_window

        wx.Panel.__init__(self, parent, -1)

        self.init_UI()

        self.Bind_EVT()

        self.init_data()

    def init_UI(self):
        def _get_scale_size(_size: tuple):
            match Config.Sys.platform:
                    case "windows":
                        return self.FromDIP(_size)
                    
                    case "linux" | "darwin":
                        return wx.DefaultSize

        ffmpeg_box = wx.StaticBox(self, -1, "FFmpeg 设置")

        ffmpeg_path_label = wx.StaticText(ffmpeg_box, -1, "FFmpeg 路径")
        self.path_box = wx.TextCtrl(ffmpeg_box, -1, size = _get_scale_size((220, 24)))
        self.browse_btn = wx.Button(ffmpeg_box, -1, "浏览", size = _get_scale_size((60, 24)))

        path_hbox = wx.BoxSizer(wx.HORIZONTAL)
        path_hbox.Add(self.path_box, 1, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, 10)
        path_hbox.Add(self.browse_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.ALIGN_CENTER, 10)

        self.auto_detect_btn = wx.Button(ffmpeg_box, -1, "自动检测", size = _get_scale_size((90, 28)))
        self.tutorial_btn = wx.Button(ffmpeg_box, -1, "安装教程", size = _get_scale_size((90, 28)))

        btn_hbox = wx.BoxSizer(wx.HORIZONTAL)
        btn_hbox.Add(self.auto_detect_btn, 0, wx.ALL & (~wx.TOP), 10)
        btn_hbox.Add(self.tutorial_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), 10)

        ffmpeg_vbox = wx.BoxSizer(wx.VERTICAL)
        ffmpeg_vbox.Add(ffmpeg_path_label, 0, wx.ALL, 10)
        ffmpeg_vbox.Add(path_hbox, 0, wx.EXPAND)
        ffmpeg_vbox.Add(btn_hbox, 0, wx.EXPAND)

        ffmpeg_sbox = wx.StaticBoxSizer(ffmpeg_box)
        ffmpeg_sbox.Add(ffmpeg_vbox, 1, wx.EXPAND)

        merge_option_box = wx.StaticBox(self, -1, "合成选项")

        self.override_file_chk = wx.CheckBox(merge_option_box, -1, "存在同名文件时覆盖原文件")
        self.m4a_to_mp3_chk = wx.CheckBox(merge_option_box, -1, "仅下载音频时将 m4a 音频转换为 mp3 格式")
        self.auto_clean_chk = wx.CheckBox(merge_option_box, -1, "合成完成后清理文件")

        merge_option_vbox = wx.BoxSizer(wx.VERTICAL)
        merge_option_vbox.Add(self.override_file_chk, 0, wx.ALL, 10)
        merge_option_vbox.Add(self.m4a_to_mp3_chk, 0, wx.ALL & (~wx.TOP), 10)
        merge_option_vbox.Add(self.auto_clean_chk, 0, wx.ALL & (~wx.TOP), 10)

        merge_option_sbox = wx.StaticBoxSizer(merge_option_box)
        merge_option_sbox.Add(merge_option_vbox, 0, wx.EXPAND)

        merge_vbox = wx.BoxSizer(wx.VERTICAL)
        merge_vbox.Add(ffmpeg_sbox, 0, wx.ALL | wx.EXPAND, 10)
        merge_vbox.Add(merge_option_sbox, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, 10)

        self.SetSizer(merge_vbox)
    
    def Bind_EVT(self):
        self.browse_btn.Bind(wx.EVT_BUTTON, self.onBrowsePath)

        self.auto_detect_btn.Bind(wx.EVT_BUTTON, self.onAutoDetect)

        self.tutorial_btn.Bind(wx.EVT_BUTTON, self.onTutorial)

    def init_data(self):
        self.path_box.SetValue(Config.FFmpeg.path)
        
        self.override_file_chk.SetValue(Config.Merge.override_file)
        self.m4a_to_mp3_chk.SetValue(Config.Merge.m4a_to_mp3)
        self.auto_clean_chk.SetValue(Config.Merge.auto_clean)

    def save(self):
        Config.FFmpeg.path = self.path_box.GetValue()
        Config.Merge.override_file = self.override_file_chk.GetValue()
        Config.Merge.m4a_to_mp3 = self.m4a_to_mp3_chk.GetValue()
        Config.Merge.auto_clean = self.auto_clean_chk.GetValue()

        kwargs = {
            "ffmpeg_path": Config.FFmpeg.path,
            "override_file": Config.Merge.override_file,
            "m4a_to_mp3": Config.Merge.m4a_to_mp3,
            "auto_clean": Config.Merge.auto_clean
        }

        utils = ConfigUtils()
        utils.update_config_kwargs(Config.APP.app_config_path, "merge", **kwargs)

    def onBrowsePath(self, event):
        default_dir = os.path.dirname(self.path_box.GetValue())

        # 根据不同平台选取不同后缀名文件
        match Config.Sys.platform:
            case "windows":
                defaultFile = "ffmpeg.exe"
                wildcard = "FFmpeg|ffmpeg.exe"

            case "linux" | "darwin":
                defaultFile = "ffmpeg"
                wildcard = "FFmpeg|*"

        dlg = wx.FileDialog(self, "选择 FFmpeg 路径", defaultDir = default_dir, defaultFile = defaultFile, style = wx.FD_OPEN, wildcard = wildcard)

        if dlg.ShowModal() == wx.ID_OK:
            save_path = dlg.GetPath()
            self.path_box.SetValue(save_path)

        dlg.Destroy()

    def onAutoDetect(self, event):
        detect_window = DetectDialog(self)

        if detect_window.ShowModal() == wx.ID_OK:
            self.path_box.SetValue(detect_window.getPath())

    def onTutorial(self, event):
        import webbrowser

        webbrowser.open("https://scott-sloan.cn/archives/120/")

    def onConfirm(self):
        self.save()

        return True

class ExtraTab(wx.Panel):
    def __init__(self, parent, _main_window):
        self._main_window = _main_window

        wx.Panel.__init__(self, parent, -1)

        self.init_UI()

        self.Bind_EVT()

        self.init_data()

    def init_UI(self):
        extra_box = wx.StaticBox(self, -1, "附加内容下载设置")

        self.get_danmaku_chk = wx.CheckBox(extra_box, -1, "下载视频弹幕")
        self.danmaku_format_lab = wx.StaticText(extra_box, -1, "弹幕文件格式")
        self.danmaku_format_choice = wx.Choice(extra_box, -1, choices = list(danmaku_format_mapping.keys()))

        danmaku_hbox = wx.BoxSizer(wx.HORIZONTAL)
        danmaku_hbox.AddSpacer(30)
        danmaku_hbox.Add(self.danmaku_format_lab, 0, wx.ALL & (~wx.BOTTOM) | wx.ALIGN_CENTER, 10)
        danmaku_hbox.Add(self.danmaku_format_choice, 0, wx.ALL & (~wx.BOTTOM) & (~wx.LEFT) | wx.ALIGN_CENTER, 10)

        self.get_subtitle_chk = wx.CheckBox(extra_box, -1, "下载视频字幕")
        self.subtitle_format_lab = wx.StaticText(extra_box, -1, "字幕文件格式")
        self.subtitle_format_choice = wx.Choice(extra_box, -1, choices = list(subtitle_format_mapping.keys()))

        subtitle_hbox = wx.BoxSizer(wx.HORIZONTAL)
        subtitle_hbox.AddSpacer(30)
        subtitle_hbox.Add(self.subtitle_format_lab, 0, wx.ALL & (~wx.BOTTOM) | wx.ALIGN_CENTER, 10)
        subtitle_hbox.Add(self.subtitle_format_choice, 0, wx.ALL & (~wx.BOTTOM) & (~wx.LEFT) | wx.ALIGN_CENTER, 10)

        self.get_cover_chk = wx.CheckBox(extra_box, -1, "下载视频封面")

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.get_danmaku_chk, 0, wx.ALL & (~wx.BOTTOM), 10)
        vbox.Add(danmaku_hbox, 0, wx.EXPAND)
        vbox.Add(self.get_subtitle_chk, 0, wx.ALL & (~wx.BOTTOM), 10)
        vbox.Add(subtitle_hbox, 0, wx.EXPAND)
        vbox.Add(self.get_cover_chk, 0, wx.ALL, 10)

        extra_sbox = wx.StaticBoxSizer(extra_box)
        extra_sbox.Add(vbox, 0, wx.EXPAND)

        extra_vbox = wx.BoxSizer(wx.VERTICAL)
        extra_vbox.Add(extra_sbox, 0, wx.ALL | wx.EXPAND, 10)

        self.SetSizer(extra_vbox)
    
    def init_data(self):
        self.get_danmaku_chk.SetValue(Config.Extra.get_danmaku)
        self.danmaku_format_choice.SetSelection(Config.Extra.danmaku_type)
        self.get_subtitle_chk.SetValue(Config.Extra.get_subtitle)
        self.subtitle_format_choice.SetSelection(Config.Extra.subtitle_type)
        self.get_cover_chk.SetValue(Config.Extra.get_cover)

        self.onChangeDanmakuEVT(0)
        self.onChangeSubtitleEVT(0)

    def Bind_EVT(self):
        self.get_danmaku_chk.Bind(wx.EVT_CHECKBOX, self.onChangeDanmakuEVT)
        self.get_subtitle_chk.Bind(wx.EVT_CHECKBOX, self.onChangeSubtitleEVT)

    def save(self):
        Config.Extra.get_danmaku = self.get_danmaku_chk.GetValue()
        Config.Extra.danmaku_type = self.danmaku_format_choice.GetSelection()
        Config.Extra.get_subtitle = self.get_subtitle_chk.GetValue()
        Config.Extra.subtitle_type = self.subtitle_format_choice.GetSelection()
        Config.Extra.get_cover = self.get_cover_chk.GetValue()

        kwargs = {
            "get_danmaku": Config.Extra.get_danmaku,
            "danmaku_type": Config.Extra.danmaku_type,
            "get_subtitle": Config.Extra.get_subtitle,
            "subtitle_type": Config.Extra.subtitle_type,
            "get_cover": Config.Extra.get_cover
        }

        utils = ConfigUtils()
        utils.update_config_kwargs(Config.APP.app_config_path, "extra", **kwargs)

    def onChangeDanmakuEVT(self, event):
        def set_enable(enable: bool):
            self.danmaku_format_choice.Enable(enable)
            self.danmaku_format_lab.Enable(enable)

        set_enable(self.get_danmaku_chk.GetValue())

    def onChangeSubtitleEVT(self, event):
        def set_enable(enable: bool):
            self.subtitle_format_choice.Enable(enable)
            self.subtitle_format_lab.Enable(enable)

        set_enable(self.get_subtitle_chk.GetValue())

    def onConfirm(self):
        self.save()

        return True

class ProxyTab(wx.Panel):
    def __init__(self, parent, _main_window):
        self._main_window = _main_window

        wx.Panel.__init__(self, parent, -1)

        self.init_UI()

        self.Bind_EVT()

        self.init_data()

    def init_UI(self):
        proxy_box = wx.StaticBox(self, -1, "代理设置")

        proxy_tip = wx.StaticText(proxy_box, -1, "代理选项")
        
        self.proxy_disable_radio = wx.RadioButton(proxy_box, -1, "不使用代理")
        self.proxy_follow_radio = wx.RadioButton(proxy_box, -1, "跟随系统")
        self.proxy_custom_radio = wx.RadioButton(proxy_box, -1, "手动设置")

        proxy_hbox = wx.BoxSizer(wx.HORIZONTAL)
        proxy_hbox.Add(self.proxy_disable_radio, 0, wx.ALL, 10)
        proxy_hbox.Add(self.proxy_follow_radio, 0, wx.ALL, 10)
        proxy_hbox.Add(self.proxy_custom_radio, 0, wx.ALL, 10)
        
        ip_lab = wx.StaticText(proxy_box, -1, "地址")
        self.ip_box = wx.TextCtrl(proxy_box, -1, size = self.FromDIP((150, 25)))

        port_lab = wx.StaticText(proxy_box, -1, "端口")
        self.port_box = wx.TextCtrl(proxy_box, -1, size = self.FromDIP((75, 25)))

        self.auth_chk = wx.CheckBox(proxy_box, -1, "启用代理身份验证")
        
        uname_lab = wx.StaticText(proxy_box, -1, "用户名")
        self.uname_box = wx.TextCtrl(proxy_box, -1, size = self.FromDIP((150, 25)))

        pwd_lab = wx.StaticText(proxy_box, -1, "密码")
        self.passwd_box = wx.TextCtrl(proxy_box, -1, size = self.FromDIP((150, 25)))

        self.test_btn = wx.Button(proxy_box, -1, "测试", size = self.FromDIP((80, 30)))

        bag_box = wx.GridBagSizer(5, 4)
        bag_box.Add(ip_lab, pos = (0, 0), flag = wx.ALL | wx.ALIGN_CENTER, border = 10)
        bag_box.Add(self.ip_box, pos = (0, 1), span = (1, 3), flag = wx.ALL & (~wx.LEFT) | wx.EXPAND, border = 10)
        bag_box.Add(port_lab, pos = (1, 0), flag = wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, border = 10)
        bag_box.Add(self.port_box, pos = (1, 1), span = (1, 2), flag = wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.EXPAND, border = 10)
        bag_box.Add(self.auth_chk, pos = (2, 0), span = (1, 2), flag = wx.ALL | wx.EXPAND, border = 10)
        bag_box.Add(uname_lab, pos = (3, 0), flag = wx.ALL | wx.ALIGN_CENTER, border = 10)
        bag_box.Add(self.uname_box, pos = (3, 1), span = (1, 3), flag = wx.ALL & (~wx.LEFT) | wx.EXPAND, border = 10)
        bag_box.Add(pwd_lab, pos = (4, 0), flag = wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, border = 10)
        bag_box.Add(self.passwd_box, pos = (4, 1), span = (1, 3), flag = wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.EXPAND, border = 10)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(proxy_tip, 0, wx.ALL & (~wx.BOTTOM), 10)
        vbox.Add(proxy_hbox, 0, wx.EXPAND)
        vbox.Add(bag_box)
        vbox.Add(self.test_btn, 0, wx.ALL, 10)

        proxy_sbox = wx.StaticBoxSizer(proxy_box)
        proxy_sbox.Add(vbox, 0, wx.EXPAND)

        proxy_vbox = wx.BoxSizer(wx.VERTICAL)
        proxy_vbox.Add(proxy_sbox, 0, wx.ALL | wx.EXPAND, 10)

        self.SetSizer(proxy_vbox)
    
    def Bind_EVT(self):
        self.proxy_disable_radio.Bind(wx.EVT_RADIOBUTTON, self.onChangeProxyModeEVT)
        self.proxy_follow_radio.Bind(wx.EVT_RADIOBUTTON, self.onChangeProxyModeEVT)
        self.proxy_custom_radio.Bind(wx.EVT_RADIOBUTTON, self.onChangeProxyModeEVT)

        self.auth_chk.Bind(wx.EVT_CHECKBOX, self.onChangeAuthEVT)
        
        self.test_btn.Bind(wx.EVT_BUTTON, self.onTestEVT)

    def init_data(self):
        match Config.Proxy.proxy_mode:
            case Config.Type.PROXY_DISABLE:
                self.proxy_disable_radio.SetValue(True)

            case Config.Type.PROXY_FOLLOW:
                self.proxy_follow_radio.SetValue(True)

            case Config.Type.PROXY_CUSTOM:
                self.proxy_custom_radio.SetValue(True)

        self.ip_box.SetValue(Config.Proxy.proxy_ip)
        self.port_box.SetValue(str(Config.Proxy.proxy_port) if Config.Proxy.proxy_port is not None else "")
    
        self.auth_chk.SetValue(Config.Proxy.enable_auth)
        self.uname_box.SetValue(Config.Proxy.auth_username)
        self.passwd_box.SetValue(Config.Proxy.auth_password)

        self.onChangeProxyModeEVT(None)
        self.onChangeAuthEVT(None)

    def save(self):
        if self.proxy_disable_radio.GetValue():
            proxy = Config.Type.PROXY_DISABLE

        elif self.proxy_follow_radio.GetValue():
            proxy = Config.Type.PROXY_FOLLOW

        else:
            proxy = Config.Type.PROXY_CUSTOM

        Config.Proxy.proxy_mode = proxy
        Config.Proxy.proxy_ip = self.ip_box.GetValue()
        Config.Proxy.proxy_port = int(self.port_box.GetValue()) if self.port_box.GetValue() != "" else None
        Config.Proxy.enable_auth = self.auth_chk.GetValue()
        Config.Proxy.auth_username = self.uname_box.GetValue()
        Config.Proxy.auth_password = self.passwd_box.GetValue()

        kwargs = {
            "proxy_mode": Config.Proxy.proxy_mode,
            "proxy_ip": Config.Proxy.proxy_ip,
            "proxy_port": Config.Proxy.proxy_port,
            "enable_auth": Config.Proxy.enable_auth,
            "auth_username": Config.Proxy.auth_username,
            "auth_password": Config.Proxy.auth_password
        }

        utils = ConfigUtils()
        utils.update_config_kwargs(Config.APP.app_config_path, "proxy", **kwargs)

    def onChangeProxyModeEVT(self, event):
        def set_enable(enable: bool):
            self.ip_box.Enable(enable)
            self.port_box.Enable(enable)

        if self.proxy_disable_radio.GetValue():
            set_enable(False)

        elif self.proxy_follow_radio.GetValue():
            set_enable(False)

        else:
            set_enable(True)

    def onChangeAuthEVT(self, event):
        def set_enable(enable: bool):
            self.uname_box.Enable(enable)
            self.passwd_box.Enable(enable)

        set_enable(self.auth_chk.GetValue())
 
    def onTestEVT(self, event):
        def test():
            try:
                start_time = time.time()

                url = "https://www.bilibili.com"
                req = requests.get(url, headers = RequestTool.get_headers(), proxies = proxy, auth = auth, timeout = 5)
                
                end_time = time.time()

                wx.MessageDialog(self, f"测试成功\n\n请求站点：{url}\n状态码：{req.status_code}\n耗时：{round(end_time - start_time, 1)}s", "提示", wx.ICON_INFORMATION).ShowModal()

            except requests.RequestException as e:
                wx.MessageDialog(self, f"测试失败\n\n请求站点：{url}\n错误信息：\n\n{e}", "测试代理", wx.ICON_WARNING).ShowModal()

        if self.proxy_custom_radio.GetValue():
            proxy = {
                "http": f"{self.ip_box.GetValue()}:{self.port_box.GetValue()}",
                "https": f"{self.ip_box.GetValue()}:{self.port_box.GetValue()}"
            }
        else:
            proxy = {}

        if self.auth_chk.GetValue():
            auth = HTTPProxyAuth(
                self.uname_box.GetValue(),
                self.passwd_box.GetValue()
            )
        else:
            auth = HTTPProxyAuth(None, None)

        Thread(target = test).start()

    def onConfirm(self):
        self.save()

        return True

class MiscTab(wx.Panel):
    def __init__(self, parent, _main_window):
        self._main_window = _main_window

        wx.Panel.__init__(self, parent, -1)

        self.init_UI()

        self.Bind_EVT()

        self.init_data()

    def init_UI(self):
        def _get_scale_size(_size: tuple):
            match Config.Sys.platform:
                case "windows":
                    return self.FromDIP(_size)
                
                case "linux" | "darwin":
                    return wx.DefaultSize

        def _get_panel_size():
            match Config.Sys.platform:
                case "windows":
                    return self.FromDIP((-1, 380))
                
                case "linux" | "darwin":
                    return self.FromDIP((400, 430))

        def _layout():
            self.scrolled_panel.Layout()

            self.scrolled_panel.sizer.Layout()

            self.scrolled_panel.SetupScrolling(scroll_x = False, scrollToTop = False)

        self.scrolled_panel = ScrolledPanel(self, _get_panel_size())
        
        sections_box = wx.StaticBox(self.scrolled_panel, -1, "剧集列表显示设置")

        self.episodes_single_choice = wx.RadioButton(sections_box, -1, "获取单个视频")
        self.episodes_in_section_choice = wx.RadioButton(sections_box, -1, "获取视频所在的合集")
        self.episodes_all_sections_choice = wx.RadioButton(sections_box, -1, "获取全部相关视频 (包括花絮、PV、OP、ED 等)")

        self.show_episode_full_name = wx.CheckBox(sections_box, -1, "显示完整剧集名称")
        self.auto_select_chk = wx.CheckBox(sections_box, -1, "自动勾选全部视频")

        sections_vbox = wx.BoxSizer(wx.VERTICAL)
        sections_vbox.Add(self.episodes_single_choice, 0, wx.ALL, 10)
        sections_vbox.Add(self.episodes_in_section_choice, 0, wx.ALL & (~wx.TOP), 10)
        sections_vbox.Add(self.episodes_all_sections_choice, 0, wx.ALL & (~wx.TOP), 10)
        sections_vbox.Add(self.show_episode_full_name, 0, wx.ALL & (~wx.BOTTOM), 10)
        sections_vbox.Add(self.auto_select_chk, 0, wx.ALL, 10)
        
        sections_sbox = wx.StaticBoxSizer(sections_box)
        sections_sbox.Add(sections_vbox, 0, wx.EXPAND)

        player_box = wx.StaticBox(self.scrolled_panel, -1, "播放器设置")

        path_lab = wx.StaticText(player_box, -1, "播放器路径")
        self.player_default_rdbtn = wx.RadioButton(player_box, -1, "系统默认")
        self.player_custom_rdbtn = wx.RadioButton(player_box, -1, "手动设置")

        player_hbox = wx.BoxSizer(wx.HORIZONTAL)
        player_hbox.Add(self.player_default_rdbtn, 0, wx.ALL & (~wx.TOP), 10)
        player_hbox.Add(self.player_custom_rdbtn, 0, wx.ALL & (~wx.TOP), 10)

        self.player_path_box = wx.TextCtrl(player_box, -1, size = _get_scale_size((220, 24)))
        self.browse_player_btn = wx.Button(player_box, -1, "浏览", size = _get_scale_size((60, 24)))

        player_path_hbox = wx.BoxSizer(wx.HORIZONTAL)
        player_path_hbox.Add(self.player_path_box, 1, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, 10)
        player_path_hbox.Add(self.browse_player_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.ALIGN_CENTER, 10)
        
        player_vbox = wx.BoxSizer(wx.VERTICAL)
        player_vbox.Add(path_lab, 0, wx.ALL, 10)
        player_vbox.Add(player_hbox, 0, wx.EXPAND)
        player_vbox.Add(player_path_hbox, 1, wx.EXPAND)

        player_sbox = wx.StaticBoxSizer(player_box)
        player_sbox.Add(player_vbox, 1, wx.EXPAND)

        misc_box = wx.StaticBox(self.scrolled_panel, -1, "杂项")
        self.check_update_chk = wx.CheckBox(misc_box, -1, "自动检查更新")
        self.debug_chk = wx.CheckBox(misc_box, -1, "启用调试模式")

        self.clear_userdata_btn = wx.Button(misc_box, -1, "清除用户数据", size = _get_scale_size((100, 28)))
        self.reset_default_btn = wx.Button(misc_box, -1, "恢复默认设置", size = _get_scale_size((100, 28)))
        
        btn_hbox = wx.BoxSizer(wx.HORIZONTAL)
        btn_hbox.Add(self.clear_userdata_btn, 0, wx.ALL, 10)
        btn_hbox.Add(self.reset_default_btn, 0, wx.ALL & (~wx.LEFT), 10)

        misc_vbox = wx.BoxSizer(wx.VERTICAL)
        misc_vbox.Add(self.check_update_chk, 0, wx.ALL, 10)
        misc_vbox.Add(self.debug_chk, 0, wx.ALL & ~(wx.TOP), 10)
        misc_vbox.Add(btn_hbox, 0, wx.EXPAND)

        misc_sbox = wx.StaticBoxSizer(misc_box)
        misc_sbox.Add(misc_vbox, 0, wx.EXPAND)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(sections_sbox, 0, wx.ALL | wx.EXPAND, 10)
        vbox.Add(player_sbox, 0, wx.ALL | wx.EXPAND, 10)
        vbox.Add(misc_sbox, 0, wx.ALL | wx.EXPAND, 10)

        self.scrolled_panel.sizer.Add(vbox, 0, wx.EXPAND)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.scrolled_panel, 1, wx.EXPAND)

        self.SetSizer(vbox)

        _layout()

    def Bind_EVT(self):
        self.player_default_rdbtn.Bind(wx.EVT_RADIOBUTTON, self.onChangePlayerPreferenceEVT)
        self.player_custom_rdbtn.Bind(wx.EVT_RADIOBUTTON, self.onChangePlayerPreferenceEVT)

        self.browse_player_btn.Bind(wx.EVT_BUTTON, self.onBrowsePlayerEVT)

        self.clear_userdata_btn.Bind(wx.EVT_BUTTON, self.onClearUserDataEVT)

    def init_data(self):
        match Config.Misc.episode_display_mode:
            case Config.Type.EPISODES_SINGLE:
                self.episodes_single_choice.SetValue(True)

            case Config.Type.EPISODES_IN_SECTION:
                self.episodes_in_section_choice.SetValue(True)
                
            case Config.Type.EPISODES_ALL_SECTIONS:
                self.episodes_all_sections_choice.SetValue(True)

        match Config.Misc.player_preference:
            case Config.Type.PLAYER_PREFERENCE_DEFAULT:
                self.player_default_rdbtn.SetValue(True)

            case Config.Type.PLAYER_PREFERENCE_CUSTOM:
                self.player_custom_rdbtn.SetValue(True)

        self.show_episode_full_name.SetValue(Config.Misc.show_episode_full_name)
        self.auto_select_chk.SetValue(Config.Misc.auto_select)
        self.player_path_box.SetValue(Config.Misc.player_path)
        self.check_update_chk.SetValue(Config.Misc.auto_check_update)
        self.debug_chk.SetValue(Config.Misc.enable_debug)

        self.onChangePlayerPreferenceEVT(None)

    def save(self):
        if self.episodes_single_choice.GetValue():
            Config.Misc.episode_display_mode = Config.Type.EPISODES_SINGLE

        elif self.episodes_in_section_choice.GetValue():
            Config.Misc.episode_display_mode = Config.Type.EPISODES_IN_SECTION

        else:
            Config.Misc.episode_display_mode = Config.Type.EPISODES_ALL_SECTIONS

        if self.player_default_rdbtn.GetValue():
            Config.Misc.player_preference = Config.Type.PLAYER_PREFERENCE_DEFAULT
        else:
            Config.Misc.player_preference = Config.Type.PLAYER_PREFERENCE_CUSTOM

        Config.Misc.auto_select = self.auto_select_chk.GetValue()
        Config.Misc.player_path = self.player_path_box.GetValue()
        Config.Misc.auto_check_update = self.check_update_chk.GetValue()
        Config.Misc.enable_debug = self.debug_chk.GetValue()

        kwargs = {
            "episode_display_mode": Config.Misc.episode_display_mode,
            "show_episode_full_name": Config.Misc.show_episode_full_name,
            "auto_select": Config.Misc.auto_select,
            "player_preference": Config.Misc.player_preference,
            "player_path": Config.Misc.player_path,
            "auto_check_update": Config.Misc.auto_check_update,
            "enable_debug": Config.Misc.enable_debug
        }

        utils = ConfigUtils()
        utils.update_config_kwargs(Config.APP.app_config_path, "misc", **kwargs)

        # 重新创建主窗口的菜单
        self._main_window.init_menubar()

    def onBrowsePlayerEVT(self, event):
        # 根据不同平台选取不同后缀名文件
        match Config.Sys.platform:
            case "windows":
                wildcard = "可执行文件(*.exe)|*.exe"

            case "linux" | "darwin":
                wildcard = "可执行文件|*"

        dialog = wx.FileDialog(self, "选择播放器路径", os.getcwd(), wildcard = wildcard, style = wx.FD_OPEN)

        if dialog.ShowModal() == wx.ID_OK:
            self.player_path_box.SetValue(dialog.GetPath())
    
    def onChangePlayerPreferenceEVT(self, event):
        def set_enable(enable: bool):
            self.player_path_box.Enable(enable)
            self.browse_player_btn.Enable(enable)

        if self.player_default_rdbtn.GetValue():
            set_enable(False)
        else:
            set_enable(True)

    def onClearUserDataEVT(self, event):
        dlg = wx.MessageDialog(self, "清除用户数据\n\n将清除用户登录信息、下载记录和程序设置，是否继续？\n\n清除后，程序将自动退出，请重新启动", "警告", wx.ICON_WARNING | wx.YES_NO)

        if dlg.ShowModal() == wx.ID_YES:
            utils = ConfigUtils()
            utils.clear_config()

            DownloadFileTool._clear_all_files()

            # 退出程序
            exit()

    def onConfirm(self):
        self.save()

        return True
