import wx

from gui.component.dialog import Dialog

class DuplicateDialog(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent, "重复下载")

        self.init_UI()

        self.init_utils()

        self.CenterOnParent()

        wx.Bell()

    def init_UI(self):
        tip_lab = wx.StaticText(self, -1, "以下项目已在下载列表中，是否仍要继续下载？")

        self.episode_list = wx.ListCtrl(self, -1, style = wx.LC_REPORT)

        self.ok_btn = wx.Button(self, wx.ID_OK, "确定", size = self.get_scaled_size((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, "取消", size = self.get_scaled_size((80, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(self.ok_btn, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        bottom_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(tip_lab, 0, wx.ALL, 10)
        vbox.Add(self.episode_list, 1, wx.EXPAND | wx.ALL & (~wx.TOP), self.FromDIP(6))
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def init_utils(self):
        self.init_list_column()

    def init_list_column(self):
        self.episode_list.AppendColumn("序号", width = self.FromDIP(75))
        self.episode_list.AppendColumn("标题", width = self.FromDIP(350))
        self.episode_list.AppendColumn("类型", width = self.FromDIP(125))

        self.Fit()