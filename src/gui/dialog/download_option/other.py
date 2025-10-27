import wx
import gettext

from utils.config import Config
from utils.common.map import number_type_map

from gui.component.panel.panel import Panel
from gui.component.misc.tooltip import ToolTip

_ = gettext.gettext

class OtherStaticBox(Panel):
    def __init__(self, parent):
        Panel.__init__(self, parent)

        self.init_UI()

    def init_UI(self):
        other_box = wx.StaticBox(self, -1, _("其他选项"))

        self.auto_popup_chk = wx.CheckBox(other_box, -1, _("下载时自动弹出此对话框"))
        self.auto_show_download_window_chk = wx.CheckBox(other_box, -1, _("自动跳转下载窗口"))
        self.add_independent_number_chk = wx.CheckBox(other_box, -1, _("在文件名前添加独立序号"))

        self.number_type_lab = wx.StaticText(other_box, -1, _("序号类型"))
        self.number_type_choice = wx.Choice(other_box, -1, choices = list(number_type_map.keys()))
        number_type_tip = ToolTip(other_box)
        number_type_tip.set_tooltip(_("序号由文件名模板控制，如需取消序号显示，请自定义下载文件名。\n\n总是从 1 开始：每次下载时，序号都从 1 开始递增\n连贯递增：每次下载时，序号都连贯递增，退出程序后重置\n使用剧集列表序号：使用在剧集列表中显示的序号"))

        number_type_hbox = wx.BoxSizer(wx.HORIZONTAL)
        number_type_hbox.Add(self.number_type_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        number_type_hbox.Add(self.number_type_choice, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        number_type_hbox.Add(number_type_tip, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        number_type_hbox.AddSpacer(self.FromDIP(30))

        other_sbox = wx.StaticBoxSizer(other_box, wx.VERTICAL)
        other_sbox.Add(self.auto_popup_chk, 0, wx.ALL, self.FromDIP(6))
        other_sbox.Add(self.auto_show_download_window_chk, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        other_sbox.Add(self.add_independent_number_chk, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM), self.FromDIP(6))
        other_sbox.Add(number_type_hbox, 0, wx.EXPAND)

        self.SetSizer(other_sbox)

    def load_data(self):
        self.auto_popup_chk.SetValue(Config.Basic.auto_popup_option_dialog)
        self.auto_show_download_window_chk.SetValue(Config.Basic.auto_show_download_window)
        self.add_independent_number_chk.SetValue(Config.Download.add_independent_number)
        self.number_type_choice.SetSelection(Config.Download.number_type)

    def save(self):
        Config.Basic.auto_popup_option_dialog = self.auto_popup_chk.GetValue()
        Config.Basic.auto_show_download_window = self.auto_show_download_window_chk.GetValue()
        Config.Download.add_independent_number = self.add_independent_number_chk.GetValue()
        Config.Download.number_type = self.number_type_choice.GetSelection()
