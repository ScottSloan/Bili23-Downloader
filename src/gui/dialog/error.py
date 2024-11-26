import wx
import wx.adv

from utils.config import Config
from utils.data_type import ErrorLog

class ErrorInfoDialog(wx.Dialog):
    def __init__(self, parent, error_log: ErrorLog):
        self.error_log = error_log

        wx.Dialog.__init__(self, parent, -1, "错误信息")

        self.init_UI()

        self.CenterOnParent()

        self.log_box.SetFocus()

    def init_UI(self):
        def _set_dark_mode():
            if not Config.Sys.dark_mode:
                self.SetBackgroundColour("white")
                self.log_box.SetBackgroundColour("white")

        err_icon = wx.StaticBitmap(self, -1, wx.ArtProvider().GetBitmap(wx.ART_ERROR, size = self.FromDIP((28, 28))))
        self.detail_lab = wx.StaticText(self, -1, f"时间：{self.error_log.time}      返回值：{self.error_log.return_code}")

        top_hbox = wx.BoxSizer(wx.HORIZONTAL)
        top_hbox.Add(err_icon, 0, wx.ALL, 10)
        top_hbox.Add(self.detail_lab, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, 10)

        top_border = wx.StaticLine(self, -1, style = wx.HORIZONTAL)

        font: wx.Font = self.GetFont()
        font.SetFractionalPointSize(int(font.GetFractionalPointSize() + 1))

        self.log_box = wx.TextCtrl(self, -1, self.error_log.log, size = self.FromDIP((500, 230)), style = wx.TE_MULTILINE)
        self.log_box.SetFont(font)

        self.close_btn = wx.Button(self, wx.ID_CANCEL, "关闭", size = self.FromDIP((80, 28)))

        bottom_border = wx.StaticLine(self, -1, style = wx.HORIZONTAL)

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(self.close_btn, 0, wx.ALL & (~wx.LEFT), 10)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(top_hbox, 0, wx.EXPAND)
        vbox.Add(top_border, 0, wx.EXPAND)
        vbox.Add(self.log_box, 1, wx.EXPAND)
        vbox.Add(bottom_border, 0, wx.EXPAND)
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

        _set_dark_mode()
