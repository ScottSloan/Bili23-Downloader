import wx
from wx.lib.intctrl import IntCtrl

from utils.config import Config
from utils.common.map import video_quality_map, audio_quality_map, video_codec_preference_map, number_type_map
from utils.common.data.priority import video_quality_priority, audio_quality_priority, video_codec_priority

from utils.module.notification import NotificationManager

from gui.window.settings.page import Page
from gui.dialog.setting.file_name.custom_file_name_v3 import CustomFileNameDialog
from gui.dialog.setting.priority.edit import EditPriorityDialog

from gui.component.misc.tooltip import ToolTip
from gui.component.choice.choice import Choice

class DownloadPage(Page):
    def __init__(self, parent: wx.Window):
        Page.__init__(self, parent, "下载", 1)

        self.init_UI()

        self.Bind_EVT()

        self.load_data()

    def init_UI(self):
        download_box = wx.StaticBox(self.panel, -1, "下载设置")

        path_lab = wx.StaticText(download_box, -1, "下载目录")
        self.path_box = wx.TextCtrl(download_box, -1)
        self.browse_btn = wx.Button(download_box, -1, "浏览", size = self.get_scaled_size((60, 24)))

        path_hbox = wx.BoxSizer(wx.HORIZONTAL)
        path_hbox.Add(self.path_box, 1, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
        path_hbox.Add(self.browse_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.custom_file_name_btn = wx.Button(download_box, -1, "自定义下载文件名", size = self.get_scaled_size((120, 28)))

        self.max_thread_lab = wx.StaticText(download_box, -1, "多线程数：1")
        self.max_thread_slider = wx.Slider(download_box, -1, 1, 1, 10)

        self.max_download_lab = wx.StaticText(download_box, -1, "并行下载数：1")
        self.max_download_slider = wx.Slider(download_box, -1, 1, 1, 10)

        video_lab = wx.StaticText(download_box, -1, "画质优先级")
        self.video_quality_priority_btn = wx.Button(download_box, -1, "设置优先级", size = self.get_scaled_size((80, 24)))

        video_quality_hbox = wx.BoxSizer(wx.HORIZONTAL)
        video_quality_hbox.Add(video_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        video_quality_hbox.Add(self.video_quality_priority_btn, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        audio_lab = wx.StaticText(download_box, -1, "音质优先级")
        self.audio_quality_priority_btn = wx.Button(download_box, -1, "设置优先级", size = self.get_scaled_size((80, 24)))

        audio_quality_hbox = wx.BoxSizer(wx.HORIZONTAL)
        audio_quality_hbox.Add(audio_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        audio_quality_hbox.Add(self.audio_quality_priority_btn, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        codec_lab = wx.StaticText(download_box, -1, "编码格式优先级")
        self.codec_priority_btn = wx.Button(download_box, -1, "设置优先级", size = self.get_scaled_size((80, 24)))

        codec_hbox = wx.BoxSizer(wx.HORIZONTAL)
        codec_hbox.Add(codec_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        codec_hbox.Add(self.codec_priority_btn, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.speed_limit_chk = wx.CheckBox(download_box, -1, "对单个下载任务进行限速")
        self.speed_limit_lab = wx.StaticText(download_box, -1, "最高")
        self.speed_limit_box = IntCtrl(download_box, size = self.FromDIP((50, -1)), min = 1, max = 1000)
        self.speed_limit_box.SetLimited(True)
        self.speed_limit_unit_lab = wx.StaticText(download_box, -1, "MB/s")

        speed_limit_hbox = wx.BoxSizer(wx.HORIZONTAL)
        speed_limit_hbox.AddSpacer(self.FromDIP(20))
        speed_limit_hbox.Add(self.speed_limit_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        speed_limit_hbox.Add(self.speed_limit_box, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))
        speed_limit_hbox.Add(self.speed_limit_unit_lab, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.number_type_lab = wx.StaticText(download_box, -1, "序号类型")
        self.number_type_choice = wx.Choice(download_box, -1, choices = list(number_type_map.keys()))
        number_type_tip = ToolTip(download_box)
        number_type_tip.set_tooltip("总是从 1 开始：每次下载时，序号都从 1 开始递增\n连贯递增：每次下载时，序号都连贯递增，退出程序后重置\n使用剧集列表序号：使用在剧集列表中显示的序号\n\n请注意：自定义下载文件名模板需添加序号相关字段才会显示")

        number_type_hbox = wx.BoxSizer(wx.HORIZONTAL)
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
        download_sbox.Add(audio_quality_hbox, 0, wx.EXPAND)
        download_sbox.Add(codec_hbox, 0, wx.EXPAND)
        download_sbox.Add(self.speed_limit_chk, 0, wx.ALL & (~wx.BOTTOM), self.FromDIP(6))
        download_sbox.Add(speed_limit_hbox, 0, wx.EXPAND)
        download_sbox.Add(number_type_hbox, 0, wx.EXPAND)
        download_sbox.Add(self.delete_history_chk, 0, wx.ALL, self.FromDIP(6))
        download_sbox.Add(toast_hbox, 0, wx.EXPAND)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(download_sbox, 0, wx.ALL | wx.EXPAND, self.FromDIP(6))

        self.panel.SetSizer(vbox)

        super().init_UI()

    def Bind_EVT(self):
        self.browse_btn.Bind(wx.EVT_BUTTON, self.onBrowsePathEVT)
        self.custom_file_name_btn.Bind(wx.EVT_BUTTON, self.onCustomFileNameEVT)

        self.max_thread_slider.Bind(wx.EVT_SLIDER, self.onThreadSliderEVT)
        self.max_download_slider.Bind(wx.EVT_SLIDER, self.onDownloadSliderEVT)

        self.video_quality_priority_btn.Bind(wx.EVT_BUTTON, self.onSetVideoQualityPriorityEVT)
        self.audio_quality_priority_btn.Bind(wx.EVT_BUTTON, self.onSetAudioQualityPriorityEVT)
        self.codec_priority_btn.Bind(wx.EVT_BUTTON, self.onSetCodecPriorityEVT)

        self.speed_limit_chk.Bind(wx.EVT_CHECKBOX, self.onChangeSpeedLimitEVT)

        self.test_btn.Bind(wx.EVT_BUTTON, self.onTestToastEVT)

    def load_data(self):
        self.path_box.SetValue(Config.Download.path)

        Config.Temp.file_name_template_list = Config.Download.file_name_template_list.copy()
        
        self.max_thread_lab.SetLabel("多线程数：{}".format(Config.Download.max_thread_count))
        self.max_thread_slider.SetValue(Config.Download.max_thread_count)

        self.max_download_lab.SetLabel("并行下载数：{}".format(Config.Download.max_download_count))
        self.max_download_slider.SetValue(Config.Download.max_download_count)
                
        self.speed_limit_chk.SetValue(Config.Download.enable_speed_limit)
        self.number_type_choice.SetSelection(Config.Download.number_type)
        self.delete_history_chk.SetValue(Config.Download.delete_history)
        self.show_toast_chk.SetValue(Config.Download.enable_notification)

        self.speed_limit_box.SetValue(Config.Download.speed_mbps)

        self.onChangeSpeedLimitEVT(0)

    def save_data(self):
        Config.Download.path = self.path_box.GetValue()
        Config.Download.max_thread_count = self.max_thread_slider.GetValue()
        Config.Download.max_download_count = self.max_download_slider.GetValue()
        Config.Download.video_quality_id = self.video_quality_choice.GetCurrentClientData()
        Config.Download.audio_quality_id = self.audio_quality_choice.GetCurrentClientData()
        Config.Download.video_codec_id = self.codec_choice.GetCurrentClientData()
        Config.Download.number_type = self.number_type_choice.GetSelection()
        Config.Download.delete_history = self.delete_history_chk.GetValue()
        Config.Download.enable_notification = self.show_toast_chk.GetValue()
        Config.Download.enable_speed_limit = self.speed_limit_chk.GetValue()
        Config.Download.speed_mbps = self.speed_limit_box.GetValue()

        Config.Download.file_name_template_list = Config.Temp.file_name_template_list.copy()

        self.parent.download_window.adjust_download_item_count(self.max_download_slider.GetValue())

    def onValidate(self):
        if not self.path_box.GetValue():
            return self.warn("下载目录不能为空")
        
        if self.speed_limit_box.GetValue() not in range(1, 1001):
            return self.warn("速度值无效，请输入 1 到 1000 之间的整数")

        self.save_data()
    
    def onBrowsePathEVT(self, event: wx.CommandEvent):
        dlg = wx.DirDialog(self, "选择下载目录", defaultPath = self.path_box.GetValue())

        if dlg.ShowModal() == wx.ID_OK:
            self.path_box.SetValue(dlg.GetPath())

    def onCustomFileNameEVT(self, event: wx.CommandEvent):
        dlg = CustomFileNameDialog(self)
        dlg.ShowModal()

    def onThreadSliderEVT(self, event: wx.ScrollEvent):
        self.max_thread_lab.SetLabel("多线程数：{}".format(self.max_thread_slider.GetValue()))

    def onDownloadSliderEVT(self, event: wx.ScrollEvent):
        self.max_download_lab.SetLabel("并行下载数：{}".format(self.max_download_slider.GetValue()))

    def onSetVideoQualityPriorityEVT(self, event: wx.CommandEvent):
        dlg = EditPriorityDialog(self, "画质", list(video_quality_priority.keys()))
        dlg.ShowModal()

    def onSetAudioQualityPriorityEVT(self, event: wx.CommandEvent):
        dlg = EditPriorityDialog(self, "音质", list(audio_quality_priority.keys()))
        dlg.ShowModal()

    def onSetCodecPriorityEVT(self, event: wx.CommandEvent):
        dlg = EditPriorityDialog(self, "编码格式", list(video_codec_priority.keys()))
        dlg.ShowModal()

    def onChangeSpeedLimitEVT(self, event: wx.CommandEvent):
        self.speed_limit_box.Enable(self.speed_limit_chk.GetValue())
        self.speed_limit_lab.Enable(self.speed_limit_chk.GetValue())
        self.speed_limit_unit_lab.Enable(self.speed_limit_chk.GetValue())

    def onTestToastEVT(self, event: wx.CommandEvent):
        notification = NotificationManager(self)

        notification.show_toast("测试通知", "这是一则测试通知", wx.ICON_INFORMATION)