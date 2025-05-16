import wx
import os
import re
import sys
import time
import shutil
import requests
import subprocess
from requests.auth import HTTPProxyAuth

from gui.component.scrolled_panel import ScrolledPanel
from gui.component.text_ctrl import TextCtrl
from gui.component.dialog import Dialog
from gui.component.panel import Panel
from gui.component.tooltip import ToolTip

from gui.dialog.ffmpeg import DetectDialog
from gui.dialog.custom_cdn import CustomCDNDialog
from gui.dialog.custom_file_name import CustomFileNameDialog
from gui.dialog.custom_subtitle_lan import CustomLanDialog

from utils.config import Config, app_config_group
from utils.tool_v2 import RequestTool
from utils.common.thread import Thread
from utils.common.map import video_quality_map, audio_quality_map, video_codec_preference_map, danmaku_format_map, subtitle_format_map, override_option_map, number_type_map, exit_option_map, get_mapping_index_by_value
from utils.common.enums import EpisodeDisplayType, ProxyMode, PlayerMode, Platform

from utils.module.notification import NotificationManager

class SettingWindow(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent, "设置")

        self.init_UI()

        self.Bind_EVT()

        self.CenterOnParent()

    def init_UI(self):
        def get_notebook_size():
            match Platform(Config.Sys.platform):
                case Platform.Windows:
                    return self.FromDIP((315, 400))
                
                case Platform.Linux | Platform.macOS:
                    return self.FromDIP((360, 470))
                
        self.note = wx.Notebook(self, -1, size = get_notebook_size())

        self.note.AddPage(BasicTab(self.note), "基本")
        self.note.AddPage(DownloadTab(self.note), "下载")
        self.note.AddPage(AdvancedTab(self.note), "高级")
        self.note.AddPage(MergeTab(self.note), "合成")
        self.note.AddPage(ProxyTab(self.note), "代理")
        self.note.AddPage(MiscTab(self.note), "其他")

        self.ok_btn = wx.Button(self, wx.ID_OK, "确定", size = self.get_scaled_size((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, "取消", size = self.get_scaled_size((80, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer(1)
        bottom_hbox.Add(self.ok_btn, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        bottom_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.note, 0, wx.EXPAND | wx.ALL, self.FromDIP(6))
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)
    
    def Bind_EVT(self):
        self.ok_btn.Bind(wx.EVT_BUTTON, self.onConfirm)
    
    def onConfirm(self, event):
        for i in range(0, self.note.GetPageCount()):
            if not self.note.GetPage(i).onConfirm():
                return
            
        Config.save_config_group(Config, app_config_group, Config.APP.app_config_path)

        event.Skip()

class Tab(Panel):
    def __init__(self, parent):
        from gui.main_v2 import MainWindow

        Panel.__init__(self, parent)

        self.parent: MainWindow = parent.GetParent().GetParent()

    def onConfirm(self):
        self.save()

        return True

class BasicTab(Tab):
    def __init__(self, parent):
        Tab.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

        self.init_data()

    def init_UI(self):
        basic_box = wx.StaticBox(self, -1, "基本设置")

        self.listen_clipboard_chk = wx.CheckBox(basic_box, -1, "自动监听剪切板")
        exit_option_lab = wx.StaticText(basic_box, -1, "当关闭窗口时")
        self.exit_option_chk = wx.Choice(basic_box, -1, choices = list(exit_option_map.keys()))

        exit_option_hbox = wx.BoxSizer(wx.HORIZONTAL)
        exit_option_hbox.Add(exit_option_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
        exit_option_hbox.Add(self.exit_option_chk, 0, wx.ALL & (~wx.LEFT) & (~wx.TOP), self.FromDIP(6))

        self.auto_popup_option_chk = wx.CheckBox(basic_box, 0, "下载前自动弹出下载选项对话框")
        self.auto_show_download_window_chk = wx.CheckBox(basic_box, 0, "下载时自动切换到下载窗口")
        self.remember_window_status_chk = wx.CheckBox(basic_box, 0, "记住窗口的大小和位置")

        basic_sbox = wx.StaticBoxSizer(basic_box, wx.VERTICAL)
        basic_sbox.Add(self.listen_clipboard_chk, 0, wx.ALL, self.FromDIP(6))
        basic_sbox.Add(exit_option_hbox, 0, wx.EXPAND)
        basic_sbox.Add(self.auto_popup_option_chk, 0, wx.ALL, self.FromDIP(6))
        basic_sbox.Add(self.auto_show_download_window_chk, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        basic_sbox.Add(self.remember_window_status_chk, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))

        extra_box = wx.StaticBox(self, -1, "附加内容下载设置")

        self.download_danmaku_file_chk = wx.CheckBox(extra_box, -1, "下载视频弹幕")
        self.danmaku_format_lab = wx.StaticText(extra_box, -1, "弹幕文件格式")
        self.danmaku_format_choice = wx.Choice(extra_box, -1, choices = list(danmaku_format_map.keys()))

        danmaku_hbox = wx.BoxSizer(wx.HORIZONTAL)
        danmaku_hbox.AddSpacer(self.FromDIP(20))
        danmaku_hbox.Add(self.danmaku_format_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        danmaku_hbox.Add(self.danmaku_format_choice, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        danmaku_hbox.AddSpacer(self.FromDIP(20))

        self.download_subtitle_file_chk = wx.CheckBox(extra_box, -1, "下载视频字幕")
        self.subtitle_file_type_lab = wx.StaticText(extra_box, -1, "字幕文件格式")
        self.subtitle_file_type_choice = wx.Choice(extra_box, -1, choices = list(subtitle_format_map.keys()))
        self.subtitle_file_lan_type_lab = wx.StaticText(extra_box, -1, "字幕语言")
        self.subtitle_file_lan_type_btn = wx.Button(extra_box, -1, "自定义")

        subtitle_grid_box = wx.FlexGridSizer(2, 4, 0, 0)
        subtitle_grid_box.AddSpacer(self.FromDIP(20))
        subtitle_grid_box.Add(self.subtitle_file_type_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
        subtitle_grid_box.Add(self.subtitle_file_type_choice, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))
        subtitle_grid_box.AddSpacer(self.FromDIP(20))
        subtitle_grid_box.AddSpacer(self.FromDIP(20))
        subtitle_grid_box.Add(self.subtitle_file_lan_type_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
        subtitle_grid_box.Add(self.subtitle_file_lan_type_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))
        subtitle_grid_box.AddSpacer(self.FromDIP(20))

        self.download_cover_file_chk = wx.CheckBox(extra_box, -1, "下载视频封面")

        extra_sbox = wx.StaticBoxSizer(extra_box, wx.VERTICAL)
        extra_sbox.Add(self.download_danmaku_file_chk, 0, wx.ALL & (~wx.BOTTOM), self.FromDIP(6))
        extra_sbox.Add(danmaku_hbox, 0, wx.EXPAND)
        extra_sbox.Add(self.download_subtitle_file_chk, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        extra_sbox.Add(subtitle_grid_box, 0, wx.EXPAND)
        extra_sbox.Add(self.download_cover_file_chk, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        
        basic_vbox = wx.BoxSizer(wx.VERTICAL)
        basic_vbox.Add(basic_sbox, 0, wx.EXPAND | wx.ALL, self.FromDIP(6))
        basic_vbox.Add(extra_sbox, 0, wx.EXPAND | wx.ALL & (~wx.TOP), self.FromDIP(6))

        self.SetSizer(basic_vbox)

    def Bind_EVT(self):
        self.download_danmaku_file_chk.Bind(wx.EVT_CHECKBOX, self.onCheckDownloadDanmakuEVT)
        self.download_subtitle_file_chk.Bind(wx.EVT_CHECKBOX, self.onCheckDownloadSubtitleEVT)

        self.subtitle_file_lan_type_btn.Bind(wx.EVT_BUTTON, self.onCustomSubtitleLanEVT)

    def init_data(self):
        self.listen_clipboard_chk.SetValue(Config.Basic.listen_clipboard)
        self.exit_option_chk.SetSelection(Config.Basic.exit_option)
        self.auto_popup_option_chk.SetValue(Config.Basic.auto_popup_option_dialog)
        self.auto_show_download_window_chk.SetValue(Config.Basic.auto_show_download_window)
        self.remember_window_status_chk.SetValue(Config.Basic.remember_window_status)

        self.download_danmaku_file_chk.SetValue(Config.Basic.download_danmaku_file)
        self.danmaku_format_choice.SetSelection(Config.Basic.danmaku_file_type)
        self.download_subtitle_file_chk.SetValue(Config.Basic.download_subtitle_file)
        self.subtitle_file_type_choice.SetSelection(Config.Basic.subtitle_file_type)
        self.download_cover_file_chk.SetValue(Config.Basic.download_cover_file)

        self.onCheckDownloadDanmakuEVT(0)
        self.onCheckDownloadSubtitleEVT(0)

    def save(self):
        Config.Basic.listen_clipboard = self.listen_clipboard_chk.GetValue()
        Config.Basic.exit_option = self.exit_option_chk.GetSelection()
        Config.Basic.auto_popup_option_dialog = self.auto_popup_option_chk.GetValue()
        Config.Basic.auto_show_download_window = self.auto_show_download_window_chk.GetValue()
        Config.Basic.remember_window_status = self.remember_window_status_chk.GetValue()

        Config.Basic.download_danmaku_file = self.download_danmaku_file_chk.GetValue()
        Config.Basic.danmaku_file_type = self.danmaku_format_choice.GetSelection()
        Config.Basic.download_subtitle_file = self.download_subtitle_file_chk.GetValue()
        Config.Basic.subtitle_file_type = self.subtitle_file_type_choice.GetSelection()
        Config.Basic.download_cover_file = self.download_cover_file_chk.GetValue()

        Config.Basic.show_exit_dialog = False

    def onCheckDownloadDanmakuEVT(self, event):
        enable = self.download_danmaku_file_chk.GetValue()
        
        self.danmaku_format_choice.Enable(enable)
        self.danmaku_format_lab.Enable(enable)

    def onCheckDownloadSubtitleEVT(self, event):
        enable = self.download_subtitle_file_chk.GetValue()

        self.subtitle_file_type_choice.Enable(enable)
        self.subtitle_file_type_lab.Enable(enable)
        self.subtitle_file_lan_type_lab.Enable(enable)
        self.subtitle_file_lan_type_btn.Enable(enable)

    def onCustomSubtitleLanEVT(self, event):
        dlg = CustomLanDialog(self)

        if dlg.ShowModal() == wx.ID_OK:
            dlg.set_option()

class DownloadTab(Tab):
    def __init__(self, parent):
        Tab.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

        self.init_data()

    def init_UI(self):
        def layout():
            self.scrolled_panel.Layout()

            self.scrolled_panel.SetupScrolling(scroll_x = False, scrollToTop = False)

        self.scrolled_panel = ScrolledPanel(self)

        download_box = wx.StaticBox(self.scrolled_panel, -1, "下载设置")

        path_lab = wx.StaticText(download_box, -1, "下载目录")
        self.path_box = TextCtrl(download_box, -1)
        self.browse_btn = wx.Button(download_box, -1, "浏览", size = self.get_scaled_size((60, 24)))

        path_hbox = wx.BoxSizer(wx.HORIZONTAL)
        path_hbox.Add(self.path_box, 1, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))
        path_hbox.Add(self.browse_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        
        self.max_thread_lab = wx.StaticText(download_box, -1, "多线程数：1")
        self.max_thread_slider = wx.Slider(download_box, -1, 1, 1, 10)

        self.max_download_lab = wx.StaticText(download_box, -1, "并行下载数：1")
        self.max_download_slider = wx.Slider(download_box, -1, 1, 1, 10)

        video_lab = wx.StaticText(download_box, -1, "默认下载清晰度")
        self.video_quality_choice = wx.Choice(download_box, -1, choices = list(video_quality_map.keys()))
        self.video_quality_tip = ToolTip(download_box)
        self.video_quality_tip.set_tooltip("指定下载视频的清晰度，取决于视频的支持情况；若视频无所选的清晰度，则自动下载最高可用的清晰度\n\n自动：自动下载每个视频的最高可用的清晰度")

        video_quality_hbox = wx.BoxSizer(wx.HORIZONTAL)
        video_quality_hbox.Add(video_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        video_quality_hbox.Add(self.video_quality_choice, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        video_quality_hbox.Add(self.video_quality_tip, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        audio_lab = wx.StaticText(download_box, -1, "默认下载音质")
        self.audio_quality_choice = wx.Choice(download_box, -1, choices = list(audio_quality_map.keys()))
        self.audio_quality_tip = ToolTip(download_box)
        self.audio_quality_tip.set_tooltip("指定下载视频的音质，取决于视频的支持情况；若视频无所选的音质，则自动下载最高可用的音质\n\n自动：自动下载每个视频的最高可用音质")

        sound_quality_hbox = wx.BoxSizer(wx.HORIZONTAL)
        sound_quality_hbox.Add(audio_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        sound_quality_hbox.Add(self.audio_quality_choice, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        sound_quality_hbox.Add(self.audio_quality_tip, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        codec_lab = wx.StaticText(download_box, -1, "视频编码格式")
        self.codec_choice = wx.Choice(download_box, -1, choices = list(video_codec_preference_map.keys()))
        self.codec_tip = ToolTip(download_box)
        self.codec_tip.set_tooltip("指定下载视频的编码格式，取决于视频的支持情况；若视频无所选的编码格式，则默认使用 AVC/H.264 编码\n\n杜比视界和HDR 视频仅支持 HEVC/H.265 编码")

        codec_hbox = wx.BoxSizer(wx.HORIZONTAL)
        codec_hbox.Add(codec_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        codec_hbox.Add(self.codec_choice, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        codec_hbox.Add(self.codec_tip, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.speed_limit_chk = wx.CheckBox(download_box, -1, "对单个下载任务进行限速")
        self.speed_limit_lab = wx.StaticText(download_box, -1, "最高")
        self.speed_limit_box = TextCtrl(download_box, -1, size = self.FromDIP((50, 25)))
        self.speed_limit_unit_lab = wx.StaticText(download_box, -1, "MB/s")

        speed_limit_hbox = wx.BoxSizer(wx.HORIZONTAL)
        speed_limit_hbox.AddSpacer(self.FromDIP(20))
        speed_limit_hbox.Add(self.speed_limit_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        speed_limit_hbox.Add(self.speed_limit_box, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))
        speed_limit_hbox.Add(self.speed_limit_unit_lab, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.auto_add_number_chk = wx.CheckBox(download_box, -1, "自动添加序号")
        self.number_type_lab = wx.StaticText(download_box, -1, "序号类型")
        self.number_type_choice = wx.Choice(download_box, -1, choices = list(number_type_map.keys()))
        number_type_tip = ToolTip(download_box)
        number_type_tip.set_tooltip("总是从 1 开始：每次下载时，序号都从 1 开始递增\n连贯递增：每次下载时，序号都连贯递增，退出程序后重置\n使用剧集列表序号：使用在剧集列表中显示的序号\n\n请注意：自定义下载文件名需添加 {number} 或者 {number_with_zero} 字段才会显示")

        number_type_hbox = wx.BoxSizer(wx.HORIZONTAL)
        number_type_hbox.AddSpacer(self.FromDIP(20))
        number_type_hbox.Add(self.number_type_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        number_type_hbox.Add(self.number_type_choice, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        number_type_hbox.Add(number_type_tip, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.delete_history_chk = wx.CheckBox(download_box, -1, "下载完成后清除本地下载记录")

        self.show_toast_chk = wx.CheckBox(download_box, -1, "允许弹出通知提示")
        self.test_btn = wx.Button(download_box, -1, "测试", size = self.get_scaled_size((60, 24)))

        toast_hbox = wx.BoxSizer(wx.HORIZONTAL)
        toast_hbox.Add(self.show_toast_chk, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        toast_hbox.Add(self.test_btn, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        download_sbox = wx.StaticBoxSizer(download_box, wx.VERTICAL)
        download_sbox.Add(path_lab, 0, wx.ALL, self.FromDIP(6))
        download_sbox.Add(path_hbox, 0, wx.EXPAND)
        download_sbox.Add(self.max_thread_lab, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        download_sbox.Add(self.max_thread_slider, 0, wx.EXPAND | wx.ALL & (~wx.TOP), self.FromDIP(6))
        download_sbox.Add(self.max_download_lab, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        download_sbox.Add(self.max_download_slider, 0, wx.EXPAND | wx.ALL & (~wx.TOP), self.FromDIP(6))
        download_sbox.Add(video_quality_hbox, 0, wx.EXPAND)
        download_sbox.Add(sound_quality_hbox, 0, wx.EXPAND)
        download_sbox.Add(codec_hbox, 0, wx.EXPAND)
        download_sbox.Add(self.speed_limit_chk, 0, wx.ALL & (~wx.BOTTOM), self.FromDIP(6))
        download_sbox.Add(speed_limit_hbox, 0, wx.EXPAND)
        download_sbox.Add(self.auto_add_number_chk, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM), self.FromDIP(6))
        download_sbox.Add(number_type_hbox, 0, wx.EXPAND)
        download_sbox.Add(self.delete_history_chk, 0, wx.ALL, self.FromDIP(6))
        download_sbox.Add(toast_hbox, 0, wx.EXPAND)

        self.scrolled_panel.sizer.Add(download_sbox, 0, wx.ALL | wx.EXPAND, self.FromDIP(6))

        download_vbox = wx.BoxSizer(wx.VERTICAL)
        download_vbox.Add(self.scrolled_panel, 1, wx.EXPAND)

        self.SetSizer(download_vbox)

        layout()

    def Bind_EVT(self):
        self.browse_btn.Bind(wx.EVT_BUTTON, self.onBrowsePathEVT)

        self.max_thread_slider.Bind(wx.EVT_SLIDER, self.onThreadCountSlideEVT)
        self.max_download_slider.Bind(wx.EVT_SLIDER, self.onDownloadCountSlideEVT)

        self.speed_limit_chk.Bind(wx.EVT_CHECKBOX, self.onChangeSpeedLimitEVT)

        self.auto_add_number_chk.Bind(wx.EVT_CHECKBOX, self.onCheckAutoAddNumberEVT)

        self.test_btn.Bind(wx.EVT_BUTTON, self.onTestToastEVT)

    def init_data(self):
        self.path_box.SetValue(Config.Download.path)
        
        self.max_thread_lab.SetLabel("多线程数：{}".format(Config.Download.max_thread_count))
        self.max_thread_slider.SetValue(Config.Download.max_thread_count)

        self.max_download_lab.SetLabel("并行下载数：{}".format(Config.Download.max_download_count))
        self.max_download_slider.SetValue(Config.Download.max_download_count)
        
        self.video_quality_choice.SetSelection(get_mapping_index_by_value(video_quality_map, Config.Download.video_quality_id))
        self.audio_quality_choice.SetSelection(get_mapping_index_by_value(audio_quality_map, Config.Download.audio_quality_id))

        self.codec_choice.SetSelection(get_mapping_index_by_value(video_codec_preference_map, Config.Download.video_codec_id))

        self.speed_limit_chk.SetValue(Config.Download.enable_speed_limit)
        self.auto_add_number_chk.SetValue(Config.Download.auto_add_number)
        self.number_type_choice.SetSelection(Config.Download.number_type)
        self.delete_history_chk.SetValue(Config.Download.delete_history)
        self.show_toast_chk.SetValue(Config.Download.enable_notification)

        self.speed_limit_box.SetValue(str(Config.Download.speed_mbps))

        self.onChangeSpeedLimitEVT(0)
        self.onCheckAutoAddNumberEVT(0)

    def save(self):
        def update_download_window():
            self.parent.download_window.downloading_page.max_download_choice.SetSelection(Config.Download.max_download_count - 1)

            self.parent.download_window.downloading_page.onMaxDownloadChangeEVT(None)

        Config.Download.path = self.path_box.GetValue()
        Config.Download.max_thread_count = self.max_thread_slider.GetValue()
        Config.Download.max_download_count = self.max_download_slider.GetValue()
        Config.Download.video_quality_id = video_quality_map[self.video_quality_choice.GetStringSelection()]
        Config.Download.audio_quality_id = audio_quality_map[self.audio_quality_choice.GetStringSelection()]
        Config.Download.video_codec_id = video_codec_preference_map[self.codec_choice.GetStringSelection()]
        Config.Download.auto_add_number = self.auto_add_number_chk.GetValue()
        Config.Download.number_type = self.number_type_choice.GetSelection()
        Config.Download.delete_history = self.delete_history_chk.GetValue()
        Config.Download.enable_notification = self.show_toast_chk.GetValue()
        Config.Download.enable_speed_limit = self.speed_limit_chk.GetValue()
        Config.Download.speed_mbps = int(self.speed_limit_box.GetValue())

        # 更新下载窗口中并行下载数信息
        update_download_window()
        
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

    def isValidSpeedLimit(self, speed):
        return bool(re.fullmatch(r'[1-9]\d*', speed))

    def onTestToastEVT(self, event):
        notification = NotificationManager(self)

        notification.show_toast("测试通知", "这是一则测试通知", wx.ICON_INFORMATION)

    def onCheckAutoAddNumberEVT(self, event):
        enable = self.auto_add_number_chk.GetValue()

        self.number_type_lab.Enable(enable)
        self.number_type_choice.Enable(enable)

class AdvancedTab(Tab):
    def __init__(self, parent, ):
        Tab.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

        self.init_data()

    def init_UI(self):
        cdn_box = wx.StaticBox(self, -1, "CDN 设置")

        self.enable_switch_cdn_chk = wx.CheckBox(cdn_box, -1, "替换音视频流 CDN host")
        self.enable_custom_cdn_tip = ToolTip(cdn_box)
        self.enable_custom_cdn_tip.set_tooltip("因 B 站分配的 CDN 线路不稳定，容易导致下载失败，开启此选项后，将自动替换下载链接中的 CDN host\n\n请注意：使用代理时，请手动关闭此选项")
        self.custom_cdn_btn = wx.Button(cdn_box, -1, "自定义", size = self.get_scaled_size((100, 28)))

        custom_cdn_hbox = wx.BoxSizer(wx.HORIZONTAL)
        custom_cdn_hbox.Add(self.enable_switch_cdn_chk, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        custom_cdn_hbox.Add(self.enable_custom_cdn_tip, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        custom_cdn_hbox.AddStretchSpacer()
        custom_cdn_hbox.Add(self.custom_cdn_btn, 0, wx.ALL, self.FromDIP(6))

        cdn_sbox = wx.StaticBoxSizer(cdn_box, wx.VERTICAL)
        cdn_sbox.Add(custom_cdn_hbox, 0, wx.EXPAND)

        advanced_download_box = wx.StaticBox(self, -1, "高级下载设置")

        self.custom_file_name_btn = wx.Button(advanced_download_box, -1, "自定义下载文件名", size = self.get_scaled_size((120, 28)))

        button_hbox = wx.BoxSizer(wx.HORIZONTAL)
        button_hbox.Add(self.custom_file_name_btn, 0, wx.ALL, self.FromDIP(6))

        self.download_error_retry_chk = wx.CheckBox(advanced_download_box, -1, "下载出错时自动重试")
        self.download_error_retry_lab = wx.StaticText(advanced_download_box, -1, "重试次数")
        self.download_error_retry_box = wx.SpinCtrl(advanced_download_box, -1, min = 1, max = 15)

        download_error_retry_hbox = wx.BoxSizer(wx.HORIZONTAL)
        download_error_retry_hbox.AddSpacer(self.FromDIP(20))
        download_error_retry_hbox.Add(self.download_error_retry_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        download_error_retry_hbox.Add(self.download_error_retry_box, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))

        self.download_suspend_retry_chk = wx.CheckBox(advanced_download_box, -1, "下载停滞时自动重启下载")
        self.download_suspend_retry_lab = wx.StaticText(advanced_download_box, -1, "重启间隔")
        self.download_suspend_retry_box = wx.SpinCtrl(advanced_download_box, -1, min = 2, max = 15)
        self.download_suspend_retry_unit_lab = wx.StaticText(advanced_download_box, -1, "秒")

        download_suspend_retry_hbox = wx.BoxSizer(wx.HORIZONTAL)
        download_suspend_retry_hbox.AddSpacer(self.FromDIP(20))
        download_suspend_retry_hbox.Add(self.download_suspend_retry_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
        download_suspend_retry_hbox.Add(self.download_suspend_retry_box, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))
        download_suspend_retry_hbox.Add(self.download_suspend_retry_unit_lab, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.always_use_https_protocol_chk = wx.CheckBox(advanced_download_box, -1, "始终使用 HTTPS 发起请求")

        advanced_download_sbox = wx.StaticBoxSizer(advanced_download_box, wx.VERTICAL)
        advanced_download_sbox.Add(button_hbox, 0, wx.EXPAND)
        advanced_download_sbox.Add(self.download_error_retry_chk, 0, wx.ALL & (~wx.BOTTOM), self.FromDIP(6))
        advanced_download_sbox.Add(download_error_retry_hbox, 0, wx.EXPAND)
        advanced_download_sbox.Add(self.download_suspend_retry_chk, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        advanced_download_sbox.Add(download_suspend_retry_hbox, 0, wx.EXPAND)
        advanced_download_sbox.Add(self.always_use_https_protocol_chk, 0, wx.ALL, self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(cdn_sbox, 0, wx.ALL | wx.EXPAND, self.FromDIP(6))
        vbox.Add(advanced_download_sbox, 0, wx.ALL | wx.EXPAND, self.FromDIP(6))

        self.SetSizerAndFit(vbox)

    def Bind_EVT(self):
        self.enable_switch_cdn_chk.Bind(wx.EVT_CHECKBOX, self.onEnableSwitchCDNEVT)
        self.custom_cdn_btn.Bind(wx.EVT_BUTTON, self.onCustomCDNEVT)

        self.custom_file_name_btn.Bind(wx.EVT_BUTTON, self.onCustomFileNameEVT)
        self.download_error_retry_chk.Bind(wx.EVT_CHECKBOX, self.onChangeRetryEVT)
        self.download_suspend_retry_chk.Bind(wx.EVT_CHECKBOX, self.onChangeRestartEVT)

    def init_data(self):
        self.enable_switch_cdn_chk.SetValue(Config.Advanced.enable_switch_cdn)

        self.file_name_template = Config.Advanced.file_name_template
        self.datetime_format = Config.Advanced.datetime_format
        self.auto_adjust = Config.Advanced.auto_adjust_field

        self.download_error_retry_chk.SetValue(Config.Advanced.retry_when_download_error)
        self.download_error_retry_box.SetValue(Config.Advanced.download_error_retry_count)
        self.download_suspend_retry_chk.SetValue(Config.Advanced.retry_when_download_suspend)
        self.download_suspend_retry_box.SetValue(Config.Advanced.download_suspend_retry_interval)
        self.always_use_https_protocol_chk.SetValue(Config.Advanced.always_use_https_protocol)

        self.onEnableSwitchCDNEVT(0)
        self.onChangeRetryEVT(0)
        self.onChangeRestartEVT(0)

    def save(self):
        Config.Advanced.enable_switch_cdn = self.enable_switch_cdn_chk.GetValue()

        Config.Advanced.file_name_template = self.file_name_template
        Config.Advanced.datetime_format = self.datetime_format
        Config.Advanced.auto_adjust_field = self.auto_adjust

        Config.Advanced.retry_when_download_error = self.download_error_retry_chk.GetValue()
        Config.Advanced.download_error_retry_count = self.download_error_retry_box.GetValue()
        Config.Advanced.retry_when_download_suspend = self.download_suspend_retry_chk.GetValue()
        Config.Advanced.download_suspend_retry_interval = self.download_suspend_retry_box.GetValue()
        Config.Advanced.always_use_https_protocol = self.always_use_https_protocol_chk.GetValue()

    def onEnableSwitchCDNEVT(self, event):        
        self.custom_cdn_btn.Enable(self.enable_switch_cdn_chk.GetValue())

    def onCustomCDNEVT(self, event):
        dlg = CustomCDNDialog(self)

        if dlg.ShowModal() == wx.ID_OK:
            dlg.saveCDNList()

    def onCustomFileNameEVT(self, event):
        dlg = CustomFileNameDialog(self, self.file_name_template, self.datetime_format, self.auto_adjust)

        if dlg.ShowModal() == wx.ID_OK:
            self.file_name_template = dlg.template_box.GetValue()
            self.datetime_format = dlg.datetime_format_box.GetValue()
            self.auto_adjust = dlg.auto_adjust_chk.GetValue()
    
    def onChangeRetryEVT(self, event):
        self.download_error_retry_lab.Enable(self.download_error_retry_chk.GetValue())
        self.download_error_retry_box.Enable(self.download_error_retry_chk.GetValue())

    def onChangeRestartEVT(self, event):
        self.download_suspend_retry_lab.Enable(self.download_suspend_retry_chk.GetValue())
        self.download_suspend_retry_box.Enable(self.download_suspend_retry_chk.GetValue())
        self.download_suspend_retry_unit_lab.Enable(self.download_suspend_retry_chk.GetValue())

class MergeTab(Tab):
    def __init__(self, parent):
        Tab.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

        self.init_data()

    def init_UI(self):
        ffmpeg_box = wx.StaticBox(self, -1, "FFmpeg 设置")

        ffmpeg_path_label = wx.StaticText(ffmpeg_box, -1, "FFmpeg 路径")
        self.path_box = TextCtrl(ffmpeg_box, -1)
        self.browse_btn = wx.Button(ffmpeg_box, -1, "浏览", size = self.get_scaled_size((60, 24)))

        path_hbox = wx.BoxSizer(wx.HORIZONTAL)
        path_hbox.Add(self.path_box, 1, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
        path_hbox.Add(self.browse_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.auto_detect_btn = wx.Button(ffmpeg_box, -1, "自动检测", size = self.get_scaled_size((90, 28)))
        self.tutorial_btn = wx.Button(ffmpeg_box, -1, "安装教程", size = self.get_scaled_size((90, 28)))

        self.check_ffmpeg_chk = wx.CheckBox(ffmpeg_box, -1, "启动时自动检查 FFmpeg 可用性")

        btn_hbox = wx.BoxSizer(wx.HORIZONTAL)
        btn_hbox.Add(self.auto_detect_btn, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        btn_hbox.Add(self.tutorial_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))

        ffmpeg_sbox = wx.StaticBoxSizer(ffmpeg_box, wx.VERTICAL)
        ffmpeg_sbox.Add(ffmpeg_path_label, 0, wx.ALL, self.FromDIP(6))
        ffmpeg_sbox.Add(path_hbox, 0, wx.EXPAND)
        ffmpeg_sbox.Add(self.check_ffmpeg_chk, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        ffmpeg_sbox.Add(btn_hbox, 0, wx.EXPAND)

        merge_option_box = wx.StaticBox(self, -1, "合成选项")

        override_lab = wx.StaticText(merge_option_box, -1, "存在同名文件时")
        self.override_option_choice = wx.Choice(merge_option_box, -1, choices = list(override_option_map.keys()))

        override_hbox = wx.BoxSizer(wx.HORIZONTAL)
        override_hbox.Add(override_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        override_hbox.Add(self.override_option_choice, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.m4a_to_mp3_chk = wx.CheckBox(merge_option_box, -1, "仅下载音频时将 m4a 音频转换为 mp3 格式")

        merge_option_sbox = wx.StaticBoxSizer(merge_option_box, wx.VERTICAL)
        merge_option_sbox.Add(override_hbox, 0, wx.EXPAND)
        merge_option_sbox.Add(self.m4a_to_mp3_chk, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))

        merge_vbox = wx.BoxSizer(wx.VERTICAL)
        merge_vbox.Add(ffmpeg_sbox, 0, wx.ALL | wx.EXPAND, self.FromDIP(6))
        merge_vbox.Add(merge_option_sbox, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))

        self.SetSizer(merge_vbox)
    
    def Bind_EVT(self):
        self.browse_btn.Bind(wx.EVT_BUTTON, self.onBrowsePath)

        self.auto_detect_btn.Bind(wx.EVT_BUTTON, self.onAutoDetect)

        self.tutorial_btn.Bind(wx.EVT_BUTTON, self.onTutorial)

    def init_data(self):
        self.path_box.SetValue(Config.Merge.ffmpeg_path)
        self.check_ffmpeg_chk.SetValue(Config.Merge.ffmpeg_check_available_when_lauch)
        
        self.override_option_choice.SetSelection(get_mapping_index_by_value(override_option_map, Config.Merge.override_option))
        self.m4a_to_mp3_chk.SetValue(Config.Merge.m4a_to_mp3)

    def save(self):
        Config.Merge.ffmpeg_path = self.path_box.GetValue()
        Config.Merge.ffmpeg_check_available_when_lauch = self.check_ffmpeg_chk.GetValue()
        Config.Merge.override_option = self.override_option_choice.GetSelection()
        Config.Merge.m4a_to_mp3 = self.m4a_to_mp3_chk.GetValue()

    def onBrowsePath(self, event):
        default_dir = os.path.dirname(self.path_box.GetValue())

        # 根据不同平台选取不同后缀名文件
        match Platform(Config.Sys.platform):
            case Platform.Windows:
                defaultFile = "ffmpeg.exe"
                wildcard = "FFmpeg|ffmpeg.exe"

            case Platform.Linux | Platform.macOS:
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

        webbrowser.open("https://bili23.scott-sloan.cn/doc/install/ffmpeg.html")

class ProxyTab(Tab):
    def __init__(self, parent):
        Tab.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

        self.init_data()

    def init_UI(self):
        proxy_box = wx.StaticBox(self, -1, "代理设置")

        proxy_tip = wx.StaticText(proxy_box, -1, "代理选项")
        proxy_warning_tip = wx.StaticText(proxy_box, -1, '注意：使用代理时，请在高级选项卡中\n手动关闭"替换音视频流 CDN"选项')
        
        self.proxy_disable_radio = wx.RadioButton(proxy_box, -1, "不使用代理")
        self.proxy_follow_radio = wx.RadioButton(proxy_box, -1, "跟随系统")
        self.proxy_custom_radio = wx.RadioButton(proxy_box, -1, "手动设置")

        proxy_hbox = wx.BoxSizer(wx.HORIZONTAL)
        proxy_hbox.Add(self.proxy_disable_radio, 0, wx.ALL, self.FromDIP(6))
        proxy_hbox.Add(self.proxy_follow_radio, 0, wx.ALL, self.FromDIP(6))
        proxy_hbox.Add(self.proxy_custom_radio, 0, wx.ALL, self.FromDIP(6))
        
        ip_lab = wx.StaticText(proxy_box, -1, "地址")
        self.ip_box = TextCtrl(proxy_box, -1)
        port_lab = wx.StaticText(proxy_box, -1, "端口")
        self.port_box = TextCtrl(proxy_box, -1)

        self.auth_chk = wx.CheckBox(proxy_box, -1, "启用代理身份验证")
        
        uname_lab = wx.StaticText(proxy_box, -1, "用户名")
        self.uname_box = TextCtrl(proxy_box, -1)
        pwd_lab = wx.StaticText(proxy_box, -1, "密码")
        self.passwd_box = TextCtrl(proxy_box)

        flex_sizer = wx.GridBagSizer(0, 0)
        flex_sizer.Add(ip_lab, pos = (0, 0), flag =  wx.ALL | wx.ALIGN_CENTER, border = self.FromDIP(6))
        flex_sizer.Add(self.ip_box, pos = (0, 1), flag = wx.ALL & (~wx.LEFT) | wx.EXPAND, border = self.FromDIP(6))
        flex_sizer.Add(port_lab, pos = (1, 0), flag = wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, border = self.FromDIP(6))
        flex_sizer.Add(self.port_box, pos = (1, 1), flag = wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.EXPAND, border = self.FromDIP(6))
        flex_sizer.Add(self.auth_chk, pos = (2, 0), span = (1, 2), flag = wx.ALL, border = self.FromDIP(6))
        flex_sizer.Add(uname_lab, pos = (3, 0), flag = wx.ALL | wx.ALIGN_CENTER, border = self.FromDIP(6))
        flex_sizer.Add(self.uname_box, pos = (3, 1), flag = wx.ALL & (~wx.LEFT) | wx.EXPAND, border = self.FromDIP(6))
        flex_sizer.Add(pwd_lab, pos = (4, 0), flag = wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, border = self.FromDIP(6))
        flex_sizer.Add(self.passwd_box, pos = (4, 1), flag = wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.EXPAND, border = self.FromDIP(6))

        flex_sizer.AddGrowableCol(1)
        flex_sizer.AddGrowableRow(0)
        flex_sizer.AddGrowableRow(1)
        flex_sizer.AddGrowableRow(3)
        flex_sizer.AddGrowableRow(4)

        self.test_btn = wx.Button(proxy_box, -1, "测试", size = self.get_scaled_size((80, 30)))

        proxy_sbox = wx.StaticBoxSizer(proxy_box, wx.VERTICAL)
        proxy_sbox.Add(proxy_tip, 0, wx.ALL & (~wx.BOTTOM), self.FromDIP(6))
        proxy_sbox.Add(proxy_warning_tip, 0, wx.ALL & (~wx.BOTTOM), self.FromDIP(6))
        proxy_sbox.Add(proxy_hbox, 0, wx.EXPAND)
        proxy_sbox.Add(flex_sizer, 0, wx.EXPAND)
        proxy_sbox.Add(self.test_btn, 0, wx.ALL, self.FromDIP(6))

        proxy_vbox = wx.BoxSizer(wx.VERTICAL)
        proxy_vbox.Add(proxy_sbox, 0, wx.ALL | wx.EXPAND, self.FromDIP(6))

        self.SetSizer(proxy_vbox)
    
    def Bind_EVT(self):
        self.proxy_disable_radio.Bind(wx.EVT_RADIOBUTTON, self.onChangeProxyModeEVT)
        self.proxy_follow_radio.Bind(wx.EVT_RADIOBUTTON, self.onChangeProxyModeEVT)
        self.proxy_custom_radio.Bind(wx.EVT_RADIOBUTTON, self.onChangeProxyModeEVT)

        self.auth_chk.Bind(wx.EVT_CHECKBOX, self.onChangeAuthEVT)
        
        self.test_btn.Bind(wx.EVT_BUTTON, self.onTestEVT)

    def init_data(self):
        match ProxyMode(Config.Proxy.proxy_mode):
            case ProxyMode.Disable:
                self.proxy_disable_radio.SetValue(True)

            case ProxyMode.Follow:
                self.proxy_follow_radio.SetValue(True)

            case ProxyMode.Custom:
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
            proxy = ProxyMode.Disable.value

        elif self.proxy_follow_radio.GetValue():
            proxy = ProxyMode.Follow.value

        else:
            proxy = ProxyMode.Custom.value

        Config.Proxy.proxy_mode = proxy
        Config.Proxy.proxy_ip = self.ip_box.GetValue()
        Config.Proxy.proxy_port = int(self.port_box.GetValue()) if self.port_box.GetValue() != "" else None
        Config.Proxy.enable_auth = self.auth_chk.GetValue()
        Config.Proxy.auth_username = self.uname_box.GetValue()
        Config.Proxy.auth_password = self.passwd_box.GetValue()

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
                req = RequestTool.request_get(url, proxies = proxy, auth = _auth)
                
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
            _auth = HTTPProxyAuth(
                self.uname_box.GetValue(),
                self.passwd_box.GetValue()
            )
        else:
            _auth = HTTPProxyAuth(None, None)

        Thread(target = test).start()

class MiscTab(Tab):
    def __init__(self, parent):
        Tab.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

        self.init_data()

    def init_UI(self):
        def layout():
            self.scrolled_panel.Layout()

            self.scrolled_panel.SetupScrolling(scroll_x = False, scrollToTop = False)

        self.scrolled_panel = ScrolledPanel(self)
        
        episodes_box = wx.StaticBox(self.scrolled_panel, -1, "剧集列表显示设置")

        self.episodes_single_choice = wx.RadioButton(episodes_box, -1, "显示单个视频")
        self.episodes_in_section_choice = wx.RadioButton(episodes_box, -1, "显示视频所在的合集")
        self.episodes_all_sections_choice = wx.RadioButton(episodes_box, -1, "显示全部相关视频 (包括 PV、OP、ED 等)")

        self.show_episode_full_name = wx.CheckBox(episodes_box, -1, "显示完整剧集名称")
        self.auto_select_chk = wx.CheckBox(episodes_box, -1, "自动勾选全部视频")

        episodes_sbox = wx.StaticBoxSizer(episodes_box, wx.VERTICAL)
        episodes_sbox.Add(self.episodes_single_choice, 0, wx.ALL, self.FromDIP(6))
        episodes_sbox.Add(self.episodes_in_section_choice, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        episodes_sbox.Add(self.episodes_all_sections_choice, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        episodes_sbox.Add(self.show_episode_full_name, 0, wx.ALL & (~wx.BOTTOM), self.FromDIP(6))
        episodes_sbox.Add(self.auto_select_chk, 0, wx.ALL, self.FromDIP(6))

        player_box = wx.StaticBox(self.scrolled_panel, -1, "播放器设置")

        path_lab = wx.StaticText(player_box, -1, "播放器路径")
        self.player_default_rdbtn = wx.RadioButton(player_box, -1, "系统默认")
        self.player_custom_rdbtn = wx.RadioButton(player_box, -1, "手动设置")

        player_hbox = wx.BoxSizer(wx.HORIZONTAL)
        player_hbox.Add(self.player_default_rdbtn, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        player_hbox.Add(self.player_custom_rdbtn, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))

        self.player_path_box = TextCtrl(player_box, -1)
        self.browse_player_btn = wx.Button(player_box, -1, "浏览", size = self.get_scaled_size((60, 24)))

        player_path_hbox = wx.BoxSizer(wx.HORIZONTAL)
        player_path_hbox.Add(self.player_path_box, 1, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
        player_path_hbox.Add(self.browse_player_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        
        player_sbox = wx.StaticBoxSizer(player_box, wx.VERTICAL)
        player_sbox.Add(path_lab, 0, wx.ALL, self.FromDIP(6))
        player_sbox.Add(player_hbox, 0, wx.EXPAND)
        player_sbox.Add(player_path_hbox, 1, wx.EXPAND)

        misc_box = wx.StaticBox(self.scrolled_panel, -1, "杂项")

        self.show_user_info_chk = wx.CheckBox(misc_box, -1, "在主界面显示用户头像和昵称")
        self.check_update_chk = wx.CheckBox(misc_box, -1, "自动检查更新")
        self.debug_chk = wx.CheckBox(misc_box, -1, "启用调试模式")

        self.clear_userdata_btn = wx.Button(misc_box, -1, "清除用户数据", size = self.get_scaled_size((100, 28)))
        self.reset_default_btn = wx.Button(misc_box, -1, "恢复默认设置", size = self.get_scaled_size((100, 28)))
        
        btn_hbox = wx.BoxSizer(wx.HORIZONTAL)
        btn_hbox.Add(self.clear_userdata_btn, 0, wx.ALL, self.FromDIP(6))
        btn_hbox.Add(self.reset_default_btn, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))

        misc_sbox = wx.StaticBoxSizer(misc_box, wx.VERTICAL)
        misc_sbox.Add(self.show_user_info_chk, 0, wx.ALL, self.FromDIP(6))
        misc_sbox.Add(self.check_update_chk, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        misc_sbox.Add(self.debug_chk, 0, wx.ALL & ~(wx.TOP), self.FromDIP(6))
        misc_sbox.Add(btn_hbox, 0, wx.EXPAND)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(episodes_sbox, 0, wx.ALL | wx.EXPAND, self.FromDIP(6))
        vbox.Add(player_sbox, 0, wx.ALL | wx.EXPAND, self.FromDIP(6))
        vbox.Add(misc_sbox, 0, wx.ALL | wx.EXPAND, self.FromDIP(6))

        self.scrolled_panel.sizer.Add(vbox, 0, wx.EXPAND)

        _misc_vbox = wx.BoxSizer(wx.VERTICAL)
        _misc_vbox.Add(self.scrolled_panel, 1, wx.EXPAND)

        self.SetSizer(_misc_vbox)

        layout()

    def Bind_EVT(self):
        self.player_default_rdbtn.Bind(wx.EVT_RADIOBUTTON, self.onChangePlayerPreferenceEVT)
        self.player_custom_rdbtn.Bind(wx.EVT_RADIOBUTTON, self.onChangePlayerPreferenceEVT)

        self.browse_player_btn.Bind(wx.EVT_BUTTON, self.onBrowsePlayerEVT)

        self.clear_userdata_btn.Bind(wx.EVT_BUTTON, self.onClearUserDataEVT)
        self.reset_default_btn.Bind(wx.EVT_BUTTON, self.onResetToDefaultEVT)

    def init_data(self):
        match EpisodeDisplayType(Config.Misc.episode_display_mode):
            case EpisodeDisplayType.Single:
                self.episodes_single_choice.SetValue(True)

            case EpisodeDisplayType.In_Section:
                self.episodes_in_section_choice.SetValue(True)
                
            case EpisodeDisplayType.All:
                self.episodes_all_sections_choice.SetValue(True)

        match PlayerMode(Config.Misc.player_preference):
            case PlayerMode.Default:
                self.player_default_rdbtn.SetValue(True)

            case PlayerMode.Custom:
                self.player_custom_rdbtn.SetValue(True)

        self.show_episode_full_name.SetValue(Config.Misc.show_episode_full_name)
        self.auto_select_chk.SetValue(Config.Misc.auto_select)
        self.player_path_box.SetValue(Config.Misc.player_path)
        self.show_user_info_chk.SetValue(Config.Misc.show_user_info)
        self.check_update_chk.SetValue(Config.Misc.check_update_when_lauch)
        self.debug_chk.SetValue(Config.Misc.enable_debug)

        self.onChangePlayerPreferenceEVT(None)

    def save(self):
        if self.episodes_single_choice.GetValue():
            Config.Misc.episode_display_mode = EpisodeDisplayType.Single.value

        elif self.episodes_in_section_choice.GetValue():
            Config.Misc.episode_display_mode = EpisodeDisplayType.In_Section.value

        else:
            Config.Misc.episode_display_mode = EpisodeDisplayType.All.value

        if self.player_default_rdbtn.GetValue():
            Config.Misc.player_preference = PlayerMode.Default.value
        else:
            Config.Misc.player_preference = PlayerMode.Custom.value

        Config.Misc.auto_select = self.auto_select_chk.GetValue()
        Config.Misc.player_path = self.player_path_box.GetValue()
        Config.Misc.show_user_info = self.show_user_info_chk.GetValue()
        Config.Misc.check_update_when_lauch = self.check_update_chk.GetValue()
        Config.Misc.enable_debug = self.debug_chk.GetValue()

        # 重新创建主窗口的菜单
        self.parent.init_menubar()

    def onBrowsePlayerEVT(self, event):
        # 根据不同平台选取不同后缀名文件
        match Platform(Config.Sys.platform):
            case Platform.Windows:
                wildcard = "可执行文件(*.exe)|*.exe"

            case Platform.Linux | Platform.macOS:
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
        dlg = wx.MessageDialog(self, "清除用户数据\n\n将清除用户登录信息、下载记录和程序设置，是否继续？\n\n程序将会重新启动。", "警告", wx.ICON_WARNING | wx.YES_NO)

        if dlg.ShowModal() == wx.ID_YES:
            Config.remove_config_file(Config.APP.app_config_path)

            shutil.rmtree(Config.User.directory)

            self.restart()
    
    def onResetToDefaultEVT(self, event):
        dlg = wx.MessageDialog(self, "恢复默认设置\n\n是否要恢复默认设置？\n\n程序将会重新启动。", "警告", wx.ICON_WARNING | wx.YES_NO)

        if dlg.ShowModal() == wx.ID_YES:
            Config.remove_config_file(Config.APP.app_config_path)

            self.restart()

    def restart(self):
        python = sys.executable
        script = sys.argv[0]

        subprocess.Popen([python, script])

        sys.exit()