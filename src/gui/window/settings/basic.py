import wx
import gettext

from utils.config import Config
from utils.common.map import exit_option_map, language_map

from gui.window.settings.page import Page

from gui.component.staticbox.extra import ExtraStaticBox
from gui.component.choice.choice import Choice
from gui.component.staticbitmap.staticbitmap import StaticBitmap

_ = gettext.gettext

class BasicPage(Page):
    def __init__(self, parent: wx.Window):
        Page.__init__(self, parent, _("基本"), 0)

        self.init_UI()

        self.load_data()

    def init_UI(self):
        basic_box = wx.StaticBox(self.panel, -1, _("基本设置"))

        language_lab = wx.StaticText(basic_box, -1, _("语言"))
        self.language_choice = Choice(basic_box)
        self.language_choice.SetChoices(language_map)

        language_hbox = wx.BoxSizer(wx.HORIZONTAL)
        language_hbox.Add(language_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        language_hbox.Add(self.language_choice, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))

        info_icon = StaticBitmap(basic_box, bmp = wx.ArtProvider().GetBitmap(wx.ART_INFORMATION, size = self.FromDIP((16, 16))), size = self.FromDIP((16, 16)))
        language_tip = wx.StaticText(basic_box, -1, _("更改语言后需要重启软件才能生效"))

        language_tip_hbox = wx.BoxSizer(wx.HORIZONTAL)
        language_tip_hbox.Add(info_icon, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        language_tip_hbox.Add(language_tip, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        language_vbox = wx.BoxSizer(wx.VERTICAL)
        language_vbox.Add(language_hbox, 0, wx.EXPAND)
        language_vbox.Add(language_tip_hbox, 0, wx.EXPAND)

        self.listen_clipboard_chk = wx.CheckBox(basic_box, -1, _("自动监听剪切板"))
        exit_option_lab = wx.StaticText(basic_box, -1, _("当关闭窗口时"))
        self.exit_option_chk = wx.Choice(basic_box, -1, choices = list(exit_option_map.keys()))

        exit_option_hbox = wx.BoxSizer(wx.HORIZONTAL)
        exit_option_hbox.Add(exit_option_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
        exit_option_hbox.Add(self.exit_option_chk, 0, wx.ALL & (~wx.LEFT) & (~wx.TOP), self.FromDIP(6))

        self.auto_popup_option_chk = wx.CheckBox(basic_box, 0, _("下载前自动弹出下载选项对话框"))
        self.auto_show_download_window_chk = wx.CheckBox(basic_box, 0, _("下载时自动切换到下载窗口"))
        self.remember_window_status_chk = wx.CheckBox(basic_box, 0, _("记住窗口的大小和位置"))
        self.always_on_top_chk = wx.CheckBox(basic_box, 0, _("窗口总在最前"))

        basic_sbox = wx.StaticBoxSizer(basic_box, wx.VERTICAL)
        basic_sbox.Add(language_vbox, 0, wx.EXPAND)
        basic_sbox.Add(self.listen_clipboard_chk, 0, wx.ALL, self.FromDIP(6))
        basic_sbox.Add(exit_option_hbox, 0, wx.EXPAND)
        basic_sbox.Add(self.auto_popup_option_chk, 0, wx.ALL, self.FromDIP(6))
        basic_sbox.Add(self.auto_show_download_window_chk, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        basic_sbox.Add(self.remember_window_status_chk, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        basic_sbox.Add(self.always_on_top_chk, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))

        self.extra_box = ExtraStaticBox(self.panel, self.parent, is_setting_page = True)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(basic_sbox, 0, wx.ALL | wx.EXPAND, self.FromDIP(6))
        vbox.Add(self.extra_box, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))

        self.panel.SetSizer(vbox)

        super().init_UI()

    def load_data(self):
        Config.Temp.ass_style = Config.Basic.ass_style.copy()
        
        self.language_choice.SetCurrentSelection(Config.Basic.language)
        self.listen_clipboard_chk.SetValue(Config.Basic.listen_clipboard)
        self.exit_option_chk.SetSelection(Config.Basic.exit_option)
        self.auto_popup_option_chk.SetValue(Config.Basic.auto_popup_option_dialog)
        self.auto_show_download_window_chk.SetValue(Config.Basic.auto_show_download_window)
        self.remember_window_status_chk.SetValue(Config.Basic.remember_window_status)
        self.always_on_top_chk.SetValue(Config.Basic.always_on_top)

        self.extra_box.load_data()

    def save_data(self):
        Config.Basic.language = self.language_choice.GetCurrentClientData()
        Config.Basic.listen_clipboard = self.listen_clipboard_chk.GetValue()
        Config.Basic.exit_option = self.exit_option_chk.GetSelection()
        Config.Basic.auto_popup_option_dialog = self.auto_popup_option_chk.GetValue()
        Config.Basic.auto_show_download_window = self.auto_show_download_window_chk.GetValue()
        Config.Basic.remember_window_status = self.remember_window_status_chk.GetValue()
        Config.Basic.always_on_top = self.always_on_top_chk.GetValue()

        self.extra_box.save()

        Config.Basic.ass_style = Config.Temp.ass_style.copy()

        self.parent.utils.init_timer()

    def onValidate(self):
        self.save_data()