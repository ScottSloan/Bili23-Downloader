import wx
import gettext

from utils.config import Config

from updater import UpdaterWindow

from gui.component.window.dialog import Dialog
from gui.component.staticbitmap.staticbitmap import StaticBitmap

_ = gettext.gettext

class UpdateDialog(Dialog):
    def __init__(self, parent, info: dict):
        self.info = info
        self.force = info.get("force")

        style = wx.DEFAULT_DIALOG_STYLE & (~wx.CLOSE_BOX) & (~wx.SYSTEM_MENU) if self.force else wx.DEFAULT_DIALOG_STYLE

        self.can_close = not self.force

        Dialog.__init__(self, parent, _("检查更新"), style = style)

        self.init_UI()

        self.init_utils()

        self.CenterOnParent()

        wx.Bell()

    def init_UI(self):
        font: wx.Font = self.GetFont()
        font.SetFractionalPointSize(int(font.GetFractionalPointSize() + 3))

        info_icon = StaticBitmap(self, bmp = wx.ArtProvider().GetBitmap(wx.ART_INFORMATION, size = self.FromDIP((28, 28))), size = self.FromDIP((28, 28)))

        title_lab = wx.StaticText(self, -1, _("发现新版本"))
        title_lab.SetFont(font)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(info_icon, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        hbox.Add(title_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))

        top_border = wx.StaticLine(self, -1, style = wx.HORIZONTAL)

        font: wx.Font = self.GetFont()
        font.SetFractionalPointSize(int(font.GetFractionalPointSize() + 1))

        self.changelog = wx.TextCtrl(self, -1, self.info.get("changelog"), size = self.FromDIP((600, 320)), style = wx.TE_MULTILINE | wx.TE_READONLY | wx.BORDER_NONE)
        self.changelog.SetFont(font)
        self.changelog.SetInsertionPoint(0)

        bottom_border = wx.StaticLine(self, -1, style = wx.HORIZONTAL)

        self.ignore_version_chk = wx.CheckBox(self, -1, _("忽略此版本，下次不再提示"))
        self.ignore_version_chk.Enable(not self.force)
        self.ignore_version_chk.SetValue(not self.force)

        self.update_btn = wx.Button(self, wx.ID_OK, _("更新"), size = self.FromDIP((90, 28)))
        self.ignore_btn = wx.Button(self, wx.ID_CANCEL, _("忽略"), size = self.FromDIP((90, 28)))
        self.ignore_btn.Enable(not self.force)

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.Add(self.ignore_version_chk, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(self.update_btn, 0, wx.ALL, self.FromDIP(6))
        bottom_hbox.Add(self.ignore_btn, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))

        update_vbox = wx.BoxSizer(wx.VERTICAL)
        update_vbox.Add(hbox, 0, wx.EXPAND)
        update_vbox.Add(top_border, 0, wx.EXPAND)
        update_vbox.Add(self.changelog, 1, wx.EXPAND)
        update_vbox.Add(bottom_border, 0, wx.EXPAND)
        update_vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(update_vbox)

        self.set_dark_mode()
    
    def init_utils(self):
        self.ignore_version_chk.SetValue(Config.Misc.ignore_version == self.info.get("version_code"))
    
    def onCloseEVT(self, event: wx.CloseEvent):
        if self.can_close:
            return super().onCloseEVT(event)

    def onOKEVT(self):
        window = UpdaterWindow(self.info["download_url"])
        window.Show()
        #wx.LaunchDefaultBrowser(self.info.get("url"))

        if self.force:
            import sys
            sys.exit()
        else:
            self.Hide()

    def onCancelEVT(self):
        Config.Misc.ignore_version = self.info.get("version_code") if self.ignore_version_chk.GetValue() else 0

        Config.save_app_config()

    def set_dark_mode(self):
        if not Config.Sys.dark_mode:
            self.SetBackgroundColour("white")
            self.changelog.SetBackgroundColour("white")