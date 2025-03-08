import wx

from gui.templates import TextCtrl

class CutClipDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, "截取片段")

        self.init_UI()

        self.CenterOnParent()

    def init_UI(self):
        input_lab = wx.StaticText(self, -1, "输入")
        self.input_box = TextCtrl(self, -1, size = self.FromDIP((400, 24)))
        self.input_browse_btn = wx.Button(self, -1, "浏览", size = self.FromDIP((60, 24)))

        input_hbox = wx.BoxSizer(wx.HORIZONTAL)
        input_hbox.Add(input_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        input_hbox.Add(self.input_box, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, 10)
        input_hbox.Add(self.input_browse_btn, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, 10)

        output_lab = wx.StaticText(self, -1, "输出")
        self.output_box = TextCtrl(self, -1, size = self.FromDIP((400, 24)))
        self.output_browse_btn = wx.Button(self, -1, "浏览", size = self.FromDIP((60, 24)))

        output_hbox = wx.BoxSizer(wx.HORIZONTAL)
        output_hbox.Add(output_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, 10)
        output_hbox.Add(self.output_box, 0, wx.ALL & (~wx.LEFT) & (~wx.TOP) | wx.ALIGN_CENTER, 10)
        output_hbox.Add(self.output_browse_btn, 0, wx.ALL & (~wx.LEFT) & (~wx.TOP) | wx.ALIGN_CENTER, 10)

        start_lab = wx.StaticText(self, -1, "开始时间")
        self.start_box = TextCtrl(self, -1, "00:00:00", size = self.FromDIP((100, 24)))

        start_hbox = wx.BoxSizer(wx.HORIZONTAL)
        start_hbox.Add(start_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        start_hbox.Add(self.start_box, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, 10)

        end_lab = wx.StaticText(self, -1, "结束时间")
        self.end_box = TextCtrl(self, -1, "00:00:10", size = self.FromDIP((100, 24)))

        end_hbox = wx.BoxSizer(wx.HORIZONTAL)
        end_hbox.Add(end_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, 10)
        end_hbox.Add(self.end_box, 0, wx.ALL & (~wx.LEFT) & (~wx.TOP) | wx.ALIGN_CENTER, 10)

        self.cut_btn = wx.Button(self, -1, "截取", size = self.FromDIP((80, 30)))
        self.close_btn = wx.Button(self, wx.ID_CANCEL, "关闭", size = self.FromDIP((80, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(self.cut_btn, 0, wx.ALL, 10)
        bottom_hbox.Add(self.close_btn, 0, wx.ALL & (~wx.LEFT), 10)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(input_hbox, 0, wx.EXPAND)
        vbox.Add(output_hbox, 0, wx.EXPAND)
        vbox.Add(start_hbox, 0, wx.EXPAND)
        vbox.Add(end_hbox, 0, wx.EXPAND)
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)
