import wx
import gettext

from gui.component.window.dialog import Dialog

_ = gettext.gettext

class ChangeLogDialog(Dialog):
    def __init__(self, parent, info: dict):
        self.info = info

        Dialog.__init__(self, parent, _("当前版本更新日志"))
        
        self.init_UI()

        self.CenterOnParent()

        wx.Bell()

    def init_UI(self):
        font: wx.Font = self.GetFont()
        font.SetFractionalPointSize(int(font.GetFractionalPointSize() + 1))

        changelog_box = wx.TextCtrl(self, -1, self.info.get("changelog"), size = self.FromDIP((500, 250)), style = wx.TE_MULTILINE | wx.TE_READONLY)
        changelog_box.SetFont(font)

        close_btn = wx.Button(self, wx.ID_CANCEL, _("关闭"), size = self.get_scaled_size((80, 28)))

        dlg_vbox = wx.BoxSizer(wx.VERTICAL)
        dlg_vbox.Add(changelog_box, 0, wx.ALL, self.FromDIP(6))
        dlg_vbox.Add(close_btn, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_RIGHT, self.FromDIP(6))

        self.SetSizerAndFit(dlg_vbox)