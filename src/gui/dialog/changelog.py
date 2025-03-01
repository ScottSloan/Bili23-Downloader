import wx

from utils.config import Config

from gui.templates import TextCtrl

class ChangeLogDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, "当前版本更新日志")
        
        self.init_UI()

        self.CenterOnParent()

        wx.Bell()

    def init_UI(self):
        def _get_scale_size(_size: tuple):
            match Config.Sys.platform:
                case "windows":
                    return self.FromDIP(_size)
                
                case "linux" | "darwin":
                    return wx.DefaultSize
                
        changelog_box = TextCtrl(self, -1, Config.Temp.change_log["changelog"], size = self.FromDIP((500, 250)), style = wx.TE_MULTILINE | wx.TE_READONLY)

        close_btn = wx.Button(self, wx.ID_CANCEL, "关闭", size = _get_scale_size((80, 28)))

        dlg_vbox = wx.BoxSizer(wx.VERTICAL)
        dlg_vbox.Add(changelog_box, 0, wx.ALL, 10)
        dlg_vbox.Add(close_btn, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_RIGHT, 10)

        self.SetSizerAndFit(dlg_vbox)