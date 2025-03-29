import wx

from utils.config import Config

from gui.component.text_ctrl import TextCtrl
from gui.component.dialog import Dialog

class ChangeLogDialog(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent, "当前版本更新日志")
        
        self.init_UI()

        self.CenterOnParent()

        wx.Bell()

    def init_UI(self):
        changelog_box = TextCtrl(self, -1, Config.Temp.changelog["changelog"], size = self.FromDIP((500, 250)), style = wx.TE_MULTILINE | wx.TE_READONLY)

        close_btn = wx.Button(self, wx.ID_CANCEL, "关闭", size = self.get_scaled_size((80, 28)))

        dlg_vbox = wx.BoxSizer(wx.VERTICAL)
        dlg_vbox.Add(changelog_box, 0, wx.ALL, self.FromDIP(6))
        dlg_vbox.Add(close_btn, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_RIGHT, self.FromDIP(6))

        self.SetSizerAndFit(dlg_vbox)