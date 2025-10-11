import wx
import gettext
from wx.lib.intctrl import IntCtrl

from utils.config import Config
from utils.common.map import number_type_map
from utils.common.data.priority import video_quality_priority, audio_quality_priority, video_codec_priority, video_quality_priority_short, audio_quality_priority_short, video_codec_priority_short
from utils.common.style.icon_v4 import Icon, IconID

from utils.module.notification import NotificationManager

from gui.window.settings.page import Page
from gui.dialog.setting.file_name.custom_file_name_v3 import CustomFileNameDialog
from gui.dialog.setting.priority.edit import EditPriorityDialog
from gui.component.panel.panel import Panel
from gui.component.button.bitmap_button import BitmapButton
from gui.component.misc.tooltip import ToolTip

_ = gettext.gettext

class SliderBox(Panel):
    def __init__(self, parent: wx.Window, label: str, min_value: int, max_value: int):
        self.label = label
        self.min_value = min_value
        self.max_value = max_value

        Panel.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

    def init_UI(self):
        self.lab = wx.StaticText(self, -1, self.label)
        self.slider = wx.Slider(self, -1, 1, self.min_value, self.max_value)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.lab, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        vbox.Add(self.slider, 0, wx.EXPAND | wx.ALL & (~wx.LEFT) & (~wx.BOTTOM) & (~wx.TOP), self.FromDIP(6))

        self.SetSizer(vbox)

    def Bind_EVT(self):
        self.slider.Bind(wx.EVT_SLIDER, self.onSliderEVT)

    def SetValue(self, value: int):
        self.slider.SetValue(value)

        self.onSliderEVT(0)

    def GetValue(self):
        return self.slider.GetValue()

    def onSliderEVT(self, event: wx.CommandEvent):
        self.lab.SetLabel(f"{self.label}：{self.slider.GetValue()}")

class PriorityBox(Panel):
    def __init__(self, parent: wx.Window, setting_dlg: wx.Window, label: str, category: str, priority_data: dict, priority_data_short: dict, priority_name_str: str):
        self.setting_dlg = setting_dlg
        self.label = label
        self.category = category
        self.priority_data = priority_data
        self.priority_data_short = priority_data_short
        self.priority_name_str = priority_name_str

        Panel.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

    def init_UI(self):
        lab = wx.StaticText(self, -1, self.label)
        self.priority_box = wx.TextCtrl(self, -1, "", style = wx.TE_READONLY)
        self.priority_btn = BitmapButton(self, Icon.get_icon_bitmap(IconID.Setting), tooltip = _("设置优先级"))

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        hbox.Add(self.priority_box, 1, wx.ALL & (~wx.LEFT), self.FromDIP(6))
        hbox.Add(self.priority_btn, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))

        self.SetSizer(hbox)

    def Bind_EVT(self):
        self.priority_btn.Bind(wx.EVT_BUTTON, self.onSetPriorityEVT)

    def init_data(self):
        self.update_box(self.get_priority_setting())

    def onSetPriorityEVT(self, event: wx.CommandEvent):
        dlg = EditPriorityDialog(self.setting_dlg, self.category, self.priority_data, self.get_priority_setting())
        
        if dlg.ShowModal() == wx.ID_OK:
            priority_setting = dlg.get_priority()

            setattr(Config.Temp, self.priority_name_str, priority_setting)

            self.update_box(priority_setting)

    def update_box(self, priority_setting: list):
        priority_list = [self.priority_data_short.get(i) for i in priority_setting]

        label = " > ".join(priority_list)

        self.priority_box.SetValue(label)
        self.priority_box.SetToolTip(label)

    def get_priority_setting(self):
        return getattr(Config.Temp, self.priority_name_str)

class DownloadPage(Page):
    def __init__(self, parent: wx.Window):
        Page.__init__(self, parent, _("下载"), 1)

        self.init_UI()

        self.Bind_EVT()

        self.load_data()

    def init_UI(self):
        download_box = wx.StaticBox(self.panel, -1, _("下载设置"))

        path_lab = wx.StaticText(download_box, -1, _("下载目录"))
        self.path_box = wx.TextCtrl(download_box, -1)
        self.browse_btn = BitmapButton(download_box, Icon.get_icon_bitmap(IconID.Folder), tooltip = _("浏览"))

        self.custom_file_name_btn = wx.Button(download_box, -1, _("自定义下载文件名"), size = self.get_scaled_size((120, 28)))

        path_hbox = wx.BoxSizer(wx.HORIZONTAL)
        path_hbox.Add(self.path_box, 1, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
        path_hbox.Add(self.browse_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        path_vbox = wx.BoxSizer(wx.VERTICAL)
        path_vbox.Add(path_lab, 0, wx.ALL, self.FromDIP(6))
        path_vbox.Add(path_hbox, 0, wx.EXPAND)
        path_vbox.Add(self.custom_file_name_btn, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))

        self.max_download_slider = SliderBox(download_box, _("并行下载数"), 1, 10)

        slider_vbox = wx.BoxSizer(wx.VERTICAL)
        slider_vbox.Add(self.max_download_slider, 0, wx.ALL | wx.EXPAND, self.FromDIP(6))

        self.video_quality_priority_box = PriorityBox(download_box, self.parent, _("画质优先级"), _("画质"), video_quality_priority, video_quality_priority_short, "video_quality_priority")
        self.audio_quality_priority_box = PriorityBox(download_box, self.parent, _("音质优先级"), _("音质"), audio_quality_priority, audio_quality_priority_short, "audio_quality_priority")
        self.video_codec_priority_box = PriorityBox(download_box, self.parent, _("编码优先级"), _("编码"), video_codec_priority, video_codec_priority_short, "video_codec_priority")

        priority_vbox = wx.BoxSizer(wx.VERTICAL)
        priority_vbox.Add(self.video_quality_priority_box, 0, wx.EXPAND)
        priority_vbox.Add(self.audio_quality_priority_box, 0, wx.EXPAND)
        priority_vbox.Add(self.video_codec_priority_box, 0, wx.EXPAND)

        self.speed_limit_chk = wx.CheckBox(download_box, -1, _("对单个下载任务进行限速"))
        self.speed_limit_lab = wx.StaticText(download_box, -1, _("最高"))
        self.speed_limit_box = IntCtrl(download_box, size = self.FromDIP((50, -1)), min = 1, max = 1000)
        self.speed_limit_box.SetLimited(True)
        self.speed_limit_unit_lab = wx.StaticText(download_box, -1, "MB/s")

        speed_limit_hbox = wx.BoxSizer(wx.HORIZONTAL)
        speed_limit_hbox.AddSpacer(self.FromDIP(20))
        speed_limit_hbox.Add(self.speed_limit_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        speed_limit_hbox.Add(self.speed_limit_box, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))
        speed_limit_hbox.Add(self.speed_limit_unit_lab, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.number_type_lab = wx.StaticText(download_box, -1, _("序号类型"))
        self.number_type_choice = wx.Choice(download_box, -1, choices = list(number_type_map.keys()))
        number_type_tip = ToolTip(download_box)
        number_type_tip.set_tooltip(_("序号由文件名模板控制，如需取消序号显示，请自定义下载文件名。\n\n总是从 1 开始：每次下载时，序号都从 1 开始递增\n连贯递增：每次下载时，序号都连贯递增，退出程序后重置\n使用剧集列表序号：使用在剧集列表中显示的序号"))

        number_type_hbox = wx.BoxSizer(wx.HORIZONTAL)
        number_type_hbox.Add(self.number_type_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        number_type_hbox.Add(self.number_type_choice, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        number_type_hbox.Add(number_type_tip, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.delete_history_chk = wx.CheckBox(download_box, -1, _("下载完成后清除本地下载记录"))

        self.show_toast_chk = wx.CheckBox(download_box, -1, _("允许弹出通知提示"))
        self.test_btn = wx.Button(download_box, -1, _("测试"), size = self.get_scaled_size((60, 24)))

        toast_hbox = wx.BoxSizer(wx.HORIZONTAL)
        toast_hbox.Add(self.show_toast_chk, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        toast_hbox.Add(self.test_btn, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        download_sbox = wx.StaticBoxSizer(download_box, wx.VERTICAL)
        download_sbox.Add(path_vbox, 0, wx.EXPAND)
        download_sbox.Add(slider_vbox, 0, wx.EXPAND)
        download_sbox.Add(priority_vbox, 0, wx.EXPAND)
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

        self.speed_limit_chk.Bind(wx.EVT_CHECKBOX, self.onChangeSpeedLimitEVT)

        self.test_btn.Bind(wx.EVT_BUTTON, self.onTestToastEVT)

    def load_data(self):
        self.path_box.SetValue(Config.Download.path)

        Config.Temp.video_quality_priority = Config.Download.video_quality_priority.copy()
        Config.Temp.audio_quality_priority = Config.Download.audio_quality_priority.copy()
        Config.Temp.video_codec_priority = Config.Download.video_codec_priority.copy()

        Config.Temp.file_name_template_list = Config.Download.file_name_template_list.copy()
        Config.Temp.strict_naming = Config.Download.strict_naming
        
        self.max_download_slider.SetValue(Config.Download.max_download_count)

        self.video_quality_priority_box.init_data()
        self.audio_quality_priority_box.init_data()
        self.video_codec_priority_box.init_data()
                
        self.speed_limit_chk.SetValue(Config.Download.enable_speed_limit)
        self.number_type_choice.SetSelection(Config.Download.number_type)
        self.delete_history_chk.SetValue(Config.Download.delete_history)
        self.show_toast_chk.SetValue(Config.Download.enable_notification)

        self.speed_limit_box.SetValue(Config.Download.speed_mbps)

        self.onChangeSpeedLimitEVT(0)

    def save_data(self):
        Config.Download.video_quality_priority = Config.Temp.video_quality_priority.copy()
        Config.Download.audio_quality_priority = Config.Temp.audio_quality_priority.copy()
        Config.Download.video_codec_priority = Config.Temp.video_codec_priority.copy()

        Config.Download.path = self.path_box.GetValue()
        Config.Download.max_download_count = self.max_download_slider.GetValue()
        Config.Download.number_type = self.number_type_choice.GetSelection()
        Config.Download.delete_history = self.delete_history_chk.GetValue()
        Config.Download.enable_notification = self.show_toast_chk.GetValue()
        Config.Download.enable_speed_limit = self.speed_limit_chk.GetValue()
        Config.Download.speed_mbps = self.speed_limit_box.GetValue()

        Config.Download.file_name_template_list = Config.Temp.file_name_template_list.copy()
        Config.Download.strict_naming = Config.Temp.strict_naming

        self.parent.download_window.adjust_download_item_count(self.max_download_slider.GetValue())

    def onValidate(self):
        if not self.path_box.GetValue():
            return self.warn("下载目录不能为空")
        
        if self.speed_limit_box.GetValue() not in range(1, 1001):
            return self.warn("速度值无效，请输入 1 到 1000 之间的整数")

        self.save_data()
    
    def onBrowsePathEVT(self, event: wx.CommandEvent):
        dlg = wx.DirDialog(self, _("选择下载目录"), defaultPath = self.path_box.GetValue())

        if dlg.ShowModal() == wx.ID_OK:
            self.path_box.SetValue(dlg.GetPath())

    def onCustomFileNameEVT(self, event: wx.CommandEvent):
        dlg = CustomFileNameDialog(self)
        dlg.ShowModal()

    def onChangeSpeedLimitEVT(self, event: wx.CommandEvent):
        self.speed_limit_box.Enable(self.speed_limit_chk.GetValue())
        self.speed_limit_lab.Enable(self.speed_limit_chk.GetValue())
        self.speed_limit_unit_lab.Enable(self.speed_limit_chk.GetValue())

    def onTestToastEVT(self, event: wx.CommandEvent):
        notification = NotificationManager(self)

        notification.show_toast(_("测试通知"), _("这是一则测试通知"), wx.ICON_INFORMATION)