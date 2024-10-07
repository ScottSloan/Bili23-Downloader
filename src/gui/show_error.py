import wx
import wx.adv

from utils.tools import save_log, get_background_color

class ShowErrorDialog(wx.Dialog):
    def __init__(self, parent, log):
        self.log = log

        wx.Dialog.__init__(self, parent, -1, "错误信息")

        self.init_UI()

        self.Bind_EVT()

        self.CenterOnParent()

        self.log_box.SetFocus()

    def init_UI(self):
        err_icon = wx.StaticBitmap(self, -1, wx.ArtProvider().GetBitmap(wx.ART_ERROR, size = self.FromDIP((28, 28))))
        self.detail_lab = wx.StaticText(self, -1, f"时间：{self.log['time']}      返回值：{self.log['return_code']}")

        top_hbox = wx.BoxSizer(wx.HORIZONTAL)
        top_hbox.Add(err_icon, 0, wx.ALL, 10)
        top_hbox.Add(self.detail_lab, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, 10)

        top_border = wx.StaticLine(self, -1, style = wx.HORIZONTAL)

        log_font: wx.Font = self.GetFont()
        log_font.SetPointSize(10)

        self.log_box = wx.TextCtrl(self, -1, self.log["log"], size = self.FromDIP((500, 230)), style = wx.TE_MULTILINE)
        self.log_box.SetBackgroundColour("white")
        self.log_box.SetFont(log_font)

        self.copy_btn = wx.Button(self, -1, "保存", size = self.FromDIP((80, 28)))
        self.close_btn = wx.Button(self, wx.ID_CANCEL, "关闭", size = self.FromDIP((80, 28)))

        bottom_border = wx.StaticLine(self, -1, style = wx.HORIZONTAL)

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(self.copy_btn, 0, wx.ALL, 10)
        bottom_hbox.Add(self.close_btn, 0, wx.ALL & (~wx.LEFT), 10)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(top_hbox, 0, wx.EXPAND)
        vbox.Add(top_border, 0, wx.EXPAND)
        vbox.Add(self.log_box, 1, wx.EXPAND)
        vbox.Add(bottom_border, 0, wx.EXPAND)
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

        self.SetBackgroundColour(get_background_color())

    def Bind_EVT(self):
        self.copy_btn.Bind(wx.EVT_BUTTON, self.onSave)

    def onSave(self, event):
        save_log(self.log["return_code"], self.log["log"])

        wx.MessageDialog(self, "已保存错误信息\n\n已将错误信息保存至运行目录下的 error.log 文件中", "提示", wx.ICON_INFORMATION).ShowModal()