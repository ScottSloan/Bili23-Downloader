import wx
import gettext

from utils.config import Config

from utils.common.model.download_info import DownloadTaskInfo
from utils.common.map import download_type_map, override_option_map

from gui.component.window.dialog import Dialog
from gui.component.choice.choice import Choice

_ = gettext.gettext

class DuplicateDialog(Dialog):
    def __init__(self, parent, duplicate_episode_list: list[DownloadTaskInfo]):
        self.duplicate_episode_list = duplicate_episode_list

        Dialog.__init__(self, parent, _("确认重复下载"))

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

        self.CenterOnParent()

        wx.Bell()

    def init_UI(self):
        tip_lab = wx.StaticText(self, -1, _("以下项目已在下载列表中，是否仍要继续下载？"))
        tip2_lab = wx.StaticText(self, -1, _("请选择处理方式："))

        self.skip_radio = wx.RadioButton(self, -1, _("跳过已存在文件"), style = wx.RB_GROUP)

        self.by_settings_radio = wx.RadioButton(self, -1, _("根据设置处理"), style = 0)
        self.override_option_choice = Choice(self)
        self.override_option_choice.SetChoices(override_option_map)

        option_hbox = wx.BoxSizer(wx.HORIZONTAL)
        option_hbox.Add(self.by_settings_radio, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
        option_hbox.Add(self.override_option_choice, 0, wx.ALL & (~wx.LEFT) & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))

        option_vbox = wx.BoxSizer(wx.VERTICAL)
        option_vbox.Add(tip2_lab, 0, wx.ALL, self.FromDIP(6))
        option_vbox.Add(self.skip_radio, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        option_vbox.Add(option_hbox, 0, wx.EXPAND)

        self.episode_list = wx.ListCtrl(self, -1, size = self.FromDIP((550, 200)), style = wx.LC_REPORT)

        self.ok_btn = wx.Button(self, wx.ID_OK, _("确定"), size = self.get_scaled_size((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, _("取消"), size = self.get_scaled_size((80, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(self.ok_btn, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        bottom_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(tip_lab, 0, wx.ALL, self.FromDIP(6))
        vbox.Add(option_vbox, 0, wx.EXPAND)
        vbox.Add(self.episode_list, 1, wx.EXPAND | wx.ALL & (~wx.TOP), self.FromDIP(6))
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def Bind_EVT(self):
        self.skip_radio.Bind(wx.EVT_RADIOBUTTON, self.onRadioBtnEVT)
        self.by_settings_radio.Bind(wx.EVT_RADIOBUTTON, self.onRadioBtnEVT)

    def init_utils(self):
        self.init_list_column()
        self.init_list_data()

        self.override_option_choice.SetSelection(Config.Merge.override_option)

        self.onRadioBtnEVT(0)

    def init_list_column(self):
        self.episode_list.AppendColumn(_("列表序号"), width = self.FromDIP(60))
        self.episode_list.AppendColumn(_("标题"), width = self.FromDIP(350))
        self.episode_list.AppendColumn(_("下载类型"), width = self.FromDIP(100))

        self.Fit()

    def init_list_data(self):
        for entry in self.duplicate_episode_list:
            self.episode_list.Append([str(entry.list_number), entry.title, download_type_map.get(entry.download_type, "未知类型")])

    def onRadioBtnEVT(self, event: wx.CommandEvent):
        self.override_option_choice.Enable(self.by_settings_radio.GetValue())

    def onOKEVT(self):
        if self.skip_radio.GetValue():
            Config.Temp.duplicate_option = 0

        if self.by_settings_radio.GetValue():
            Config.Temp.duplicate_option = 1
            Config.Merge.override_option = self.override_option_choice.GetSelection()
        