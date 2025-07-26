import wx
import os
import re
import sys
import time
import shutil
import requests
import subprocess
from requests.auth import HTTPProxyAuth

from gui.component.panel.scrolled_panel import ScrolledPanel
from gui.component.text_ctrl.text_ctrl import TextCtrl
from gui.component.window.dialog import Dialog
from gui.component.panel.panel import Panel
from gui.component.misc.tooltip import ToolTip
from gui.component.staticbox.extra import ExtraStaticBox

from gui.dialog.setting.ffmpeg import DetectDialog
from gui.dialog.setting.custom_cdn_host import CustomCDNDialog
from gui.dialog.setting.custom_file_name_v2 import CustomFileNameDialog
from gui.dialog.setting.custom_user_agent import CustomUADialog

from utils.config import Config, app_config_group

from utils.common.thread import Thread
from utils.common.request import RequestUtils
from utils.common.map import video_quality_map, audio_quality_map, video_codec_preference_map, override_option_map, number_type_map, exit_option_map, webpage_option_map, get_mapping_index_by_value
from utils.common.enums import EpisodeDisplayType, ProxyMode, Platform

from utils.module.notification import NotificationManager

class SettingWindow(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent, "设置")

        self.init_UI()

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
        self.note.AddPage(FFmpegTab(self.note), "FFmpeg")
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
    
    def onOKEVT(self):
        for i in range(0, self.note.GetPageCount()):
            if not self.note.GetPage(i).onConfirm():
                return
            
        Config.save_config_group(Config, app_config_group, Config.APP.app_config_path)

class Tab(Panel):
    def __init__(self, parent):
        from gui.main_v3 import MainWindow

        Panel.__init__(self, parent)

        self.parent: MainWindow = parent.GetParent().GetParent()

    def onConfirm(self):
        self.save()

        return True

class BasicTab(Tab):
    def __init__(self, parent):
        Tab.__init__(self, parent)

        self.init_UI()

        self.init_data()

    def init_UI(self):
        self.scrolled_panel = ScrolledPanel(self)

        basic_box = wx.StaticBox(self.scrolled_panel, -1, "基本设置")

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

        self.extra_box = ExtraStaticBox(self.scrolled_panel)

        self.scrolled_panel.sizer.Add(basic_sbox, 0, wx.ALL | wx.EXPAND, self.FromDIP(6))
        self.scrolled_panel.sizer.Add(self.extra_box, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))
        
        basic_vbox = wx.BoxSizer(wx.VERTICAL)
        basic_vbox.Add(self.scrolled_panel, 1, wx.EXPAND)

        self.SetSizer(basic_vbox)

        self.scrolled_panel.Layout()

    def init_data(self):
        Config.Temp.ass_style = Config.Basic.ass_style.copy()
        
        self.listen_clipboard_chk.SetValue(Config.Basic.listen_clipboard)
        self.exit_option_chk.SetSelection(Config.Basic.exit_option)
        self.auto_popup_option_chk.SetValue(Config.Basic.auto_popup_option_dialog)
        self.auto_show_download_window_chk.SetValue(Config.Basic.auto_show_download_window)
        self.remember_window_status_chk.SetValue(Config.Basic.remember_window_status)

        self.extra_box.load_data()

    def save(self):
        Config.Basic.listen_clipboard = self.listen_clipboard_chk.GetValue()
        Config.Basic.exit_option = self.exit_option_chk.GetSelection()
        Config.Basic.auto_popup_option_dialog = self.auto_popup_option_chk.GetValue()
        Config.Basic.auto_show_download_window = self.auto_show_download_window_chk.GetValue()
        Config.Basic.remember_window_status = self.remember_window_status_chk.GetValue()

        self.extra_box.save()

        Config.Basic.ass_style = Config.Temp.ass_style.copy()

        self.parent.utils.init_timer()

class DownloadTab(Tab):
    def __init__(self, parent):
        Tab.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

        self.init_data()

    def init_UI(self):
        self.scrolled_panel = ScrolledPanel(self)

        download_box = wx.StaticBox(self.scrolled_panel, -1, "下载设置")

        path_lab = wx.StaticText(download_box, -1, "下载目录")
        self.path_box = TextCtrl(download_box, -1)
        self.browse_btn = wx.Button(download_box, -1, "浏览", size = self.get_scaled_size((60, 24)))

        path_hbox = wx.BoxSizer(wx.HORIZONTAL)
        path_hbox.Add(self.path_box, 1, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
        path_hbox.Add(self.browse_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.custom_file_name_btn = wx.Button(download_box, -1, "自定义下载文件名", size = self.get_scaled_size((120, 28)))

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
        number_type_tip.set_tooltip("总是从 1 开始：每次下载时，序号都从 1 开始递增\n连贯递增：每次下载时，序号都连贯递增，退出程序后重置\n使用剧集列表序号：使用在剧集列表中显示的序号\n\n请注意：自定义下载文件名模板需添加序号相关字段才会显示")

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
        download_sbox.Add(self.custom_file_name_btn, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
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

        self.scrolled_panel.Layout()

    def Bind_EVT(self):
        self.browse_btn.Bind(wx.EVT_BUTTON, self.onBrowsePathEVT)
        self.custom_file_name_btn.Bind(wx.EVT_BUTTON, self.onCustomFileNameEVT)

        self.max_thread_slider.Bind(wx.EVT_SLIDER, self.onThreadCountSlideEVT)
        self.max_download_slider.Bind(wx.EVT_SLIDER, self.onDownloadCountSlideEVT)

        self.speed_limit_chk.Bind(wx.EVT_CHECKBOX, self.onChangeSpeedLimitEVT)

        self.auto_add_number_chk.Bind(wx.EVT_CHECKBOX, self.onCheckAutoAddNumberEVT)

        self.test_btn.Bind(wx.EVT_BUTTON, self.onTestToastEVT)

    def init_data(self):
        self.path_box.SetValue(Config.Download.path)

        Config.Temp.file_name_template_list = Config.Download.file_name_template_list.copy()
        
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

        Config.Download.file_name_template_list = Config.Temp.file_name_template_list.copy()

        # 更新下载窗口中并行下载数信息
        update_download_window()
        
    def onConfirm(self):
        if not self.isValidSpeedLimit(self.speed_limit_box.GetValue()):
            wx.MessageDialog(self, "速度值无效\n\n输入的速度值无效，应为一个正整数", "警告", wx.ICON_WARNING).ShowModal()
            return False
        
        self.save()

        return True
    
    def onBrowsePathEVT(self, event):
        dlg = wx.DirDialog(self, "选择下载目录", defaultPath = self.path_box.GetValue())

        if dlg.ShowModal() == wx.ID_OK:
            self.path_box.SetValue(dlg.GetPath())

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

    def onCustomFileNameEVT(self, event):
        dlg = CustomFileNameDialog(self)
        dlg.ShowModal()

class AdvancedTab(Tab):
    def __init__(self, parent, ):
        Tab.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

        self.init_data()

    def init_UI(self):
        self.scrolled_panel = ScrolledPanel(self)

        cdn_box = wx.StaticBox(self.scrolled_panel, -1, "CDN 设置")

        self.enable_switch_cdn_chk = wx.CheckBox(cdn_box, -1, "替换音视频流 CDN 节点")
        self.enable_custom_cdn_tip = ToolTip(cdn_box)
        self.enable_custom_cdn_tip.set_tooltip("由于哔哩哔哩（B 站）默认分配的 CDN 线路可能存在稳定性问题，导致音视频流下载失败，建议开启`替换音视频流 CDN 节点`功能。该功能会根据您设置的优先级顺序，自动选择可用的 CDN 节点，以提升访问速度和成功率。\n\n请注意：开启代理工具时，请务必关闭此功能，避免 CDN 节点与代理线路冲突导致连接失败。")
        self.custom_cdn_btn = wx.Button(cdn_box, -1, "自定义", size = self.get_scaled_size((100, 28)))

        custom_cdn_hbox = wx.BoxSizer(wx.HORIZONTAL)
        custom_cdn_hbox.Add(self.enable_switch_cdn_chk, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        custom_cdn_hbox.Add(self.enable_custom_cdn_tip, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        custom_cdn_hbox.AddStretchSpacer()
        custom_cdn_hbox.Add(self.custom_cdn_btn, 0, wx.ALL, self.FromDIP(6))

        cdn_sbox = wx.StaticBoxSizer(cdn_box, wx.VERTICAL)
        cdn_sbox.Add(custom_cdn_hbox, 0, wx.EXPAND)

        advanced_download_box = wx.StaticBox(self.scrolled_panel, -1, "高级下载设置")

        self.download_error_retry_chk = wx.CheckBox(advanced_download_box, -1, "下载出错时自动重试")
        self.download_error_retry_lab = wx.StaticText(advanced_download_box, -1, "重试次数")
        self.download_error_retry_box = wx.SpinCtrl(advanced_download_box, -1, min = 1, max = 15)
        self.download_error_retry_unit_lab = wx.StaticText(advanced_download_box, -1, "次")

        download_error_retry_hbox = wx.BoxSizer(wx.HORIZONTAL)
        download_error_retry_hbox.AddSpacer(self.FromDIP(20))
        download_error_retry_hbox.Add(self.download_error_retry_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        download_error_retry_hbox.Add(self.download_error_retry_box, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))
        download_error_retry_hbox.Add(self.download_error_retry_unit_lab, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.download_suspend_retry_chk = wx.CheckBox(advanced_download_box, -1, "下载停滞时自动重启下载")
        self.download_suspend_retry_lab = wx.StaticText(advanced_download_box, -1, "重启间隔")
        self.download_suspend_retry_box = wx.SpinCtrl(advanced_download_box, -1, min = 2, max = 15)
        self.download_suspend_retry_unit_lab = wx.StaticText(advanced_download_box, -1, "秒")

        download_suspend_retry_hbox = wx.BoxSizer(wx.HORIZONTAL)
        download_suspend_retry_hbox.AddSpacer(self.FromDIP(20))
        download_suspend_retry_hbox.Add(self.download_suspend_retry_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
        download_suspend_retry_hbox.Add(self.download_suspend_retry_box, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))
        download_suspend_retry_hbox.Add(self.download_suspend_retry_unit_lab, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.check_md5_chk = wx.CheckBox(advanced_download_box, -1, "下载完成后进行 MD5 校验")

        self.always_use_https_protocol_chk = wx.CheckBox(advanced_download_box, -1, "始终使用 HTTPS 发起请求")

        self.custom_ua_btn = wx.Button(advanced_download_box, -1, "自定义 User-Agent", size = self.get_scaled_size((130, 28)))

        advanced_download_sbox = wx.StaticBoxSizer(advanced_download_box, wx.VERTICAL)
        advanced_download_sbox.Add(self.download_error_retry_chk, 0, wx.ALL & (~wx.BOTTOM), self.FromDIP(6))
        advanced_download_sbox.Add(download_error_retry_hbox, 0, wx.EXPAND)
        advanced_download_sbox.Add(self.download_suspend_retry_chk, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        advanced_download_sbox.Add(download_suspend_retry_hbox, 0, wx.EXPAND)
        advanced_download_sbox.Add(self.check_md5_chk, 0, wx.ALL, self.FromDIP(6))
        advanced_download_sbox.Add(self.always_use_https_protocol_chk, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        advanced_download_sbox.Add(self.custom_ua_btn, 0, wx.ALL, self.FromDIP(6))

        webpage_box = wx.StaticBox(self.scrolled_panel, -1, "Web 页面展示设置")

        webpage_lab = wx.StaticText(webpage_box, -1, "展示方式")
        self.webpage_option_choice = wx.Choice(webpage_box, -1, choices = list(webpage_option_map.keys()))
        webpage_tooltip = ToolTip(webpage_box)
        webpage_tooltip.set_tooltip("设置 Web 页面的展示方式\n\n自动检测：自动选择可用的展示方式\n使用系统 Webview 组件：在窗口中内嵌展示页面\n使用系统默认浏览器：在外部浏览器中展示页面")

        webpage_hbox = wx.BoxSizer(wx.HORIZONTAL)
        webpage_hbox.Add(webpage_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        webpage_hbox.Add(self.webpage_option_choice, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))
        webpage_hbox.Add(webpage_tooltip, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        webpage_sbox = wx.StaticBoxSizer(webpage_box, wx.VERTICAL)
        webpage_sbox.Add(webpage_hbox, 0, wx.EXPAND)

        self.scrolled_panel.sizer.Add(cdn_sbox, 0, wx.ALL | wx.EXPAND, self.FromDIP(6))
        self.scrolled_panel.sizer.Add(advanced_download_sbox, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))
        self.scrolled_panel.sizer.Add(webpage_sbox, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))

        advanced_vbox = wx.BoxSizer(wx.VERTICAL)
        advanced_vbox.Add(self.scrolled_panel, 1, wx.EXPAND)
        
        self.SetSizer(advanced_vbox)

        self.scrolled_panel.Layout()

    def Bind_EVT(self):
        self.enable_switch_cdn_chk.Bind(wx.EVT_CHECKBOX, self.onEnableSwitchCDNEVT)
        self.custom_cdn_btn.Bind(wx.EVT_BUTTON, self.onCustomCDNEVT)

        self.download_error_retry_chk.Bind(wx.EVT_CHECKBOX, self.onChangeRetryEVT)
        self.download_suspend_retry_chk.Bind(wx.EVT_CHECKBOX, self.onChangeRestartEVT)

        self.custom_ua_btn.Bind(wx.EVT_BUTTON, self.onCustomUAEVT)

    def init_data(self):
        self.enable_switch_cdn_chk.SetValue(Config.Advanced.enable_switch_cdn)
        Config.Temp.cdn_list = Config.Advanced.cdn_list.copy()

        self.download_error_retry_chk.SetValue(Config.Advanced.retry_when_download_error)
        self.download_error_retry_box.SetValue(Config.Advanced.download_error_retry_count)
        self.download_suspend_retry_chk.SetValue(Config.Advanced.retry_when_download_suspend)
        self.download_suspend_retry_box.SetValue(Config.Advanced.download_suspend_retry_interval)
        self.always_use_https_protocol_chk.SetValue(Config.Advanced.always_use_https_protocol)

        self.check_md5_chk.SetValue(Config.Advanced.check_md5)

        Config.Temp.user_agent = Config.Advanced.user_agent

        self.webpage_option_choice.SetSelection(get_mapping_index_by_value(webpage_option_map, Config.Advanced.webpage_option))

        self.onEnableSwitchCDNEVT(0)
        self.onChangeRetryEVT(0)
        self.onChangeRestartEVT(0)

    def save(self):
        Config.Advanced.enable_switch_cdn = self.enable_switch_cdn_chk.GetValue()
        Config.Advanced.cdn_list = Config.Temp.cdn_list.copy()

        Config.Advanced.retry_when_download_error = self.download_error_retry_chk.GetValue()
        Config.Advanced.download_error_retry_count = self.download_error_retry_box.GetValue()
        Config.Advanced.retry_when_download_suspend = self.download_suspend_retry_chk.GetValue()
        Config.Advanced.download_suspend_retry_interval = self.download_suspend_retry_box.GetValue()
        Config.Advanced.always_use_https_protocol = self.always_use_https_protocol_chk.GetValue()

        Config.Advanced.check_md5 = self.check_md5_chk.GetValue()

        Config.Advanced.user_agent = Config.Temp.user_agent

        Config.Advanced.webpage_option = self.webpage_option_choice.GetSelection()

    def onEnableSwitchCDNEVT(self, event):
        self.custom_cdn_btn.Enable(self.enable_switch_cdn_chk.GetValue())

    def onCustomCDNEVT(self, event):
        dlg = CustomCDNDialog(self)
        dlg.ShowModal()

    def onChangeRetryEVT(self, event):
        enable = self.download_error_retry_chk.GetValue()

        self.download_error_retry_lab.Enable(enable)
        self.download_error_retry_box.Enable(enable)
        self.download_error_retry_unit_lab.Enable(enable)

    def onChangeRestartEVT(self, event):
        enable = self.download_suspend_retry_chk.GetValue()

        self.download_suspend_retry_lab.Enable(enable)
        self.download_suspend_retry_box.Enable(enable)
        self.download_suspend_retry_unit_lab.Enable(enable)

    def onCustomUAEVT(self, event):
        dlg = CustomUADialog(self)
        dlg.ShowModal()

class FFmpegTab(Tab):
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

        merge_option_box = wx.StaticBox(self, -1, "音视频合并选项")

        self.keep_original_files_chk = wx.CheckBox(merge_option_box, -1, "合并完成后保留原始文件")
        keep_original_files_tip = ToolTip(merge_option_box)
        keep_original_files_tip.set_tooltip("合并完成后，保留原始的视频和音频文件")

        keep_original_files_hbox = wx.BoxSizer(wx.HORIZONTAL)
        keep_original_files_hbox.Add(self.keep_original_files_chk, 0, wx.ALL & (~wx.RIGHT) | wx.ALIGN_CENTER, self.FromDIP(6))
        keep_original_files_hbox.Add(keep_original_files_tip, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        override_lab = wx.StaticText(merge_option_box, -1, "存在同名文件时")
        self.override_option_choice = wx.Choice(merge_option_box, -1, choices = list(override_option_map.keys()))

        override_hbox = wx.BoxSizer(wx.HORIZONTAL)
        override_hbox.Add(override_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        override_hbox.Add(self.override_option_choice, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        merge_option_sbox = wx.StaticBoxSizer(merge_option_box, wx.VERTICAL)
        merge_option_sbox.Add(override_hbox, 0, wx.EXPAND)
        merge_option_sbox.Add(keep_original_files_hbox, 0, wx.EXPAND)

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
        self.check_ffmpeg_chk.SetValue(Config.Merge.ffmpeg_check_available_when_launch)
        
        self.override_option_choice.SetSelection(Config.Merge.override_option)
        self.keep_original_files_chk.SetValue(Config.Merge.keep_original_files)

    def save(self):
        Config.Merge.ffmpeg_path = self.path_box.GetValue()
        Config.Merge.ffmpeg_check_available_when_launch = self.check_ffmpeg_chk.GetValue()
        Config.Merge.override_option = self.override_option_choice.GetSelection()
        Config.Merge.keep_original_files = self.keep_original_files_chk.GetValue()

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
                req = RequestUtils.request_get(url, proxies = proxy, auth = _auth)
                
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

        other_box = wx.StaticBox(self.scrolled_panel, -1, "杂项")

        self.show_user_info_chk = wx.CheckBox(other_box, -1, "在主界面显示用户头像和昵称")
        self.check_update_chk = wx.CheckBox(other_box, -1, "自动检查更新")
        self.debug_chk = wx.CheckBox(other_box, -1, "启用调试模式")

        self.clear_userdata_btn = wx.Button(other_box, -1, "清除用户数据", size = self.get_scaled_size((100, 28)))
        self.reset_default_btn = wx.Button(other_box, -1, "恢复默认设置", size = self.get_scaled_size((100, 28)))
        
        btn_hbox = wx.BoxSizer(wx.HORIZONTAL)
        btn_hbox.Add(self.clear_userdata_btn, 0, wx.ALL, self.FromDIP(6))
        btn_hbox.Add(self.reset_default_btn, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))

        other_sbox = wx.StaticBoxSizer(other_box, wx.VERTICAL)
        other_sbox.Add(self.show_user_info_chk, 0, wx.ALL, self.FromDIP(6))
        other_sbox.Add(self.check_update_chk, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        other_sbox.Add(self.debug_chk, 0, wx.ALL & ~(wx.TOP), self.FromDIP(6))
        other_sbox.Add(btn_hbox, 0, wx.EXPAND)

        self.scrolled_panel.sizer.Add(episodes_sbox, 0, wx.ALL | wx.EXPAND, self.FromDIP(6))
        self.scrolled_panel.sizer.Add(other_sbox, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))

        misc_vbox = wx.BoxSizer(wx.VERTICAL)
        misc_vbox.Add(self.scrolled_panel, 1, wx.EXPAND)

        self.SetSizer(misc_vbox)

        self.scrolled_panel.Layout()

    def Bind_EVT(self):
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

        self.show_episode_full_name.SetValue(Config.Misc.show_episode_full_name)
        self.auto_select_chk.SetValue(Config.Misc.auto_check_episode_item)
        self.show_user_info_chk.SetValue(Config.Misc.show_user_info)
        self.check_update_chk.SetValue(Config.Misc.check_update_when_launch)
        self.debug_chk.SetValue(Config.Misc.enable_debug)

    def save(self):
        if self.episodes_single_choice.GetValue():
            Config.Misc.episode_display_mode = EpisodeDisplayType.Single.value

        elif self.episodes_in_section_choice.GetValue():
            Config.Misc.episode_display_mode = EpisodeDisplayType.In_Section.value

        else:
            Config.Misc.episode_display_mode = EpisodeDisplayType.All.value

        Config.Misc.auto_check_episode_item = self.auto_select_chk.GetValue()
        Config.Misc.show_user_info = self.show_user_info_chk.GetValue()
        Config.Misc.check_update_when_launch = self.check_update_chk.GetValue()
        Config.Misc.enable_debug = self.debug_chk.GetValue()

        # 重新创建主窗口的菜单
        self.parent.init_menubar()

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