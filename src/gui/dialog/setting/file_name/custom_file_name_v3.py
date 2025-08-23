import wx

from gui.component.window.dialog import Dialog

class CustomFileNameDialog(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent, "自定义下载文件名")

        self.init_UI()

        self.Bind_EVT()

        self.init_data()

        self.CenterOnParent()

    def init_UI(self):
        self.template_list = wx.ListCtrl(self, -1, style = wx.LC_REPORT)

        self.ok_btn = wx.Button(self, wx.ID_OK, "确定", size = self.FromDIP((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, "取消", size = self.FromDIP((80, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(self.ok_btn, 0, wx.ALL, self.FromDIP(6))
        bottom_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.template_list, 0, wx.ALL & (~wx.BOTTOM) | wx.EXPAND, self.FromDIP(6))
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def Bind_EVT(self):
        pass

    def init_data(self):
        self.init_list_column()
        self.init_list_data()

    def init_list_column(self):
        self.template_list.AppendColumn("序号", width = self.FromDIP(50))
        self.template_list.AppendColumn("类别", width = self.FromDIP(75))
        self.template_list.AppendColumn("子类别", width = self.FromDIP(75))
        self.template_list.AppendColumn("文件名模板", width = self.FromDIP(300))

        self.Fit()

    def init_list_data(self):
        data = [
            (1, "投稿视频", "普通", ""),
            (2, "投稿视频", "分P", ""),
            (3, "投稿视频", "合集", ""),
            (4, "投稿视频", "互动视频", ""),
            (5, "剧集", "-", ""),
            (6, "课程", "-", ""),
            (7, "个人主页", "-", ""),
            (8, "收藏夹", "-", "")
        ]

        for entry in data:
            self.template_list.Append(entry)