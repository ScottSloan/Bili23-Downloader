import wx

from utils.config import Config
from utils.common.enums import StreamType

from utils.parse.preview import PreviewInfo

from gui.dialog.download_option.media_info import MediaInfoPanel
from gui.dialog.download_option.media_option import MediaOptionStaticBox
from gui.dialog.download_option.path import PathStaticBox
from gui.dialog.download_option.other import OtherStaticBox

from gui.dialog.confirm.video_resolution import RequireVideoResolutionDialog

from gui.component.window.dialog import Dialog
from gui.component.staticbox.extra import ExtraStaticBox

class DownloadOptionDialog(Dialog):
    def __init__(self, parent: wx.Window, source: str):
        from gui.window.main.main_v3 import MainWindow

        self.parent: MainWindow = parent
        self.source = source

        Dialog.__init__(self, parent, "下载选项")

        self.init_UI()

        self.init_utils()

        self.CenterOnParent()

    def init_UI(self):
        self.media_info_box = MediaInfoPanel(self)

        self.media_option_box = MediaOptionStaticBox(self)

        self.path_box = PathStaticBox(self)

        left_vbox = wx.BoxSizer(wx.VERTICAL)
        left_vbox.Add(self.media_info_box, 0, wx.ALL | wx.EXPAND, self.FromDIP(6))
        left_vbox.AddStretchSpacer()
        left_vbox.Add(self.media_option_box, 0, wx.ALL | wx.EXPAND, self.FromDIP(6))
        left_vbox.Add(self.path_box, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))

        self.extra_box = ExtraStaticBox(self, self, is_setting_page = False)

        self.other_box = OtherStaticBox(self)

        right_vbox = wx.BoxSizer(wx.VERTICAL)
        right_vbox.Add(self.extra_box, 1, wx.ALL | wx.EXPAND, self.FromDIP(6))
        right_vbox.Add(self.other_box, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(left_vbox, 0, wx.EXPAND)
        hbox.Add(right_vbox, 0, wx.EXPAND)

        self.ok_btn = wx.Button(self, wx.ID_OK, "确定", size = self.get_scaled_size((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, "取消", size = self.get_scaled_size((80, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(self.ok_btn, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        bottom_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(hbox, 0, wx.EXPAND)
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def init_utils(self):
        def load_download_option():
            self.media_info_box.load_data()

            self.media_option_box.load_data()

            self.path_box.load_data()

            self.extra_box.load_data()

            self.other_box.load_data()

        load_download_option()

    def warn(self, message: str, flag: int = None):
        dlg = wx.MessageDialog(self, message, "警告", wx.ICON_WARNING | flag)
        dlg.SetYesNoCancelLabels("是", "否", "不再提示")

        return dlg.ShowModal()

    def check_ass_only(self):
        not_dash = StreamType(self.media_info_box.stream_type) != StreamType.Dash
        ass_danmaku = self.extra_box.danmaku_file_type_choice.GetStringSelection() == "ass" and self.extra_box.download_danmaku_file_chk.GetValue()
        ass_subtitle = self.extra_box.subtitle_file_type_choice.GetStringSelection() == "ass" and self.extra_box.download_subtitle_file_chk.GetValue()

        require_resolution = (not self.media_option_box.download_video_steam_chk.GetValue() or not_dash) and (ass_danmaku or ass_subtitle)

        if require_resolution and not Config.Temp.remember_resolution_settings:
            dlg = RequireVideoResolutionDialog(self)
            
            if dlg.ShowModal() != wx.ID_OK:
                return True

    def check_login_paid(self):
        if not Config.Basic.no_paid_check:
            if not Config.User.login:
                return self.show_dialog()
            
    def show_dialog(self):
        dlg = wx.RichMessageDialog(self, "账号未登录\n\n账号未登录，无法下载 480P 以上清晰度视频，是否继续下载？", "警告", wx.YES_NO | wx.ICON_WARNING)
        dlg.ShowCheckBox("不再提示")

        rtn = dlg.ShowModal()

        if dlg.IsCheckBoxChecked():
            Config.Basic.no_paid_check = True

            Config.save_app_config()

        return rtn == wx.ID_NO

    def onOKEVT(self):
        if not self.path_box.path_box.GetValue():
            self.warn("保存设置失败\n\n下载目录不能为空", wx.OK)
            return True

        self.media_info_box.save()
        self.media_option_box.save()
        self.path_box.save()
        self.extra_box.save()
        self.other_box.save()

        Config.save_app_config()

        if self.source == "main":
            if self.check_ass_only():
                return True
            
            if self.check_login_paid():
                return True