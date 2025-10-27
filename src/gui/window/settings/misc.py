import wx
import os
import sys
import shutil
import gettext
import subprocess

from utils.config import Config
from utils.common.enums import EpisodeDisplayType
from utils.common.io.file import File
from utils.common.io.directory import Directory

from gui.window.settings.page import Page

_ = gettext.gettext

class MiscPage(Page):
    def __init__(self, parent: wx.Window):
        Page.__init__(self, parent, _("其他"), 5)

        self.init_UI()

        self.Bind_EVT()

        self.load_data()

    def init_UI(self):
        episodes_box = wx.StaticBox(self.panel, -1, _("剧集列表显示设置"))

        self.episodes_single_choice = wx.RadioButton(episodes_box, -1, _("显示单个视频"))
        self.episodes_in_section_choice = wx.RadioButton(episodes_box, -1, _("显示视频所在的列表"))
        self.episodes_all_sections_choice = wx.RadioButton(episodes_box, -1, _("显示全部相关视频 (包括 PV、OP、ED 等)"))

        self.show_episode_full_name = wx.CheckBox(episodes_box, -1, _("显示完整剧集名称"))
        self.auto_select_chk = wx.CheckBox(episodes_box, -1, _("自动勾选全部视频"))

        episodes_sbox = wx.StaticBoxSizer(episodes_box, wx.VERTICAL)
        episodes_sbox.Add(self.episodes_single_choice, 0, wx.ALL, self.FromDIP(6))
        episodes_sbox.Add(self.episodes_in_section_choice, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        episodes_sbox.Add(self.episodes_all_sections_choice, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        episodes_sbox.Add(self.show_episode_full_name, 0, wx.ALL & (~wx.BOTTOM), self.FromDIP(6))
        episodes_sbox.Add(self.auto_select_chk, 0, wx.ALL, self.FromDIP(6))

        other_box = wx.StaticBox(self.panel, -1, _("杂项"))

        self.show_user_info_chk = wx.CheckBox(other_box, -1, _("在主界面显示用户头像和昵称"))
        self.debug_chk = wx.CheckBox(other_box, -1, _("启用调试模式"))

        self.clear_userdata_btn = wx.Button(other_box, -1, _("清除用户数据"), size = self.get_scaled_size((100, 28)))
        self.reset_default_btn = wx.Button(other_box, -1, _("恢复默认设置"), size = self.get_scaled_size((100, 28)))

        btn_hbox = wx.BoxSizer(wx.HORIZONTAL)
        btn_hbox.Add(self.clear_userdata_btn, 0, wx.ALL, self.FromDIP(6))
        btn_hbox.Add(self.reset_default_btn, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))

        self.open_config_btn = wx.Button(other_box, -1, _("打开配置文件夹"), size = self.get_scaled_size((120, 28)))

        other_sbox = wx.StaticBoxSizer(other_box, wx.VERTICAL)
        other_sbox.Add(self.show_user_info_chk, 0, wx.ALL, self.FromDIP(6))
        other_sbox.Add(self.debug_chk, 0, wx.ALL & ~(wx.TOP), self.FromDIP(6))
        other_sbox.Add(btn_hbox, 0, wx.EXPAND)
        other_sbox.Add(self.open_config_btn, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(episodes_sbox, 0, wx.ALL | wx.EXPAND, self.FromDIP(6))
        vbox.Add(other_sbox, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))

        self.panel.SetSizer(vbox)

        super().init_UI()

    def Bind_EVT(self):
        self.clear_userdata_btn.Bind(wx.EVT_BUTTON, self.onClearUserDataEVT)
        self.reset_default_btn.Bind(wx.EVT_BUTTON, self.onResetToDefaultEVT)
        self.open_config_btn.Bind(wx.EVT_BUTTON, self.onOpenConfigFolderEVT)

    def load_data(self):
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
        self.debug_chk.SetValue(Config.Misc.enable_debug)

    def save_data(self):
        if self.episodes_single_choice.GetValue():
            Config.Misc.episode_display_mode = EpisodeDisplayType.Single.value

        elif self.episodes_in_section_choice.GetValue():
            Config.Misc.episode_display_mode = EpisodeDisplayType.In_Section.value

        else:
            Config.Misc.episode_display_mode = EpisodeDisplayType.All.value

        Config.Misc.auto_check_episode_item = self.auto_select_chk.GetValue()
        Config.Misc.show_user_info = self.show_user_info_chk.GetValue()
        Config.Misc.enable_debug = self.debug_chk.GetValue()

    def onValidate(self):
        self.save_data()
        
    def onClearUserDataEVT(self, event: wx.CommandEvent):
        dlg = wx.MessageDialog(self, _("清除用户数据\n\n将清除用户登录信息、下载记录和程序设置，是否继续？\n\n程序将会重新启动。"), _("警告"), wx.ICON_WARNING | wx.YES_NO)

        if dlg.ShowModal() == wx.ID_YES:
            files = [
                Config.User.user_config_path,
                Config.APP.lang_config_path,
                Config.APP.history_file_path,
                Config.APP.err_log_path
            ]

            File.remove_files(files)

            shutil.rmtree(Config.User.directory)

            self.restart()
    
    def onResetToDefaultEVT(self, event: wx.CommandEvent):
        dlg = wx.MessageDialog(self, _("恢复默认设置\n\n是否恢复默认设置？\n\n程序将会重新启动。"), _("警告"), wx.ICON_WARNING | wx.YES_NO)

        if dlg.ShowModal() == wx.ID_YES:
            File.remove_file(Config.APP.app_config_path)

            self.restart()

    def onOpenConfigFolderEVT(self, event: wx.CommandEvent):
        Directory.open_directory(Config.User.directory)

    def restart(self):
        if pystand := os.environ.get("PYSTAND"):
            subprocess.Popen(pystand)

        elif not sys.argv[0].endswith(".py"):
            subprocess.Popen(sys.argv)

        else:
            subprocess.Popen([sys.executable] + sys.argv)

        sys.exit()