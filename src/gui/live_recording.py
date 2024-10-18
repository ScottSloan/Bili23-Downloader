import wx

from utils.live import LiveInfo

class LiveRecordingWindow(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, "直播录制")

        self.init_UI()

        self.CenterOnParent()

        self.init_live_info()

    def init_UI(self):
        font: wx.Font = self.GetFont()
        font.SetPointSize(12)

        self.title_lab = wx.StaticText(self, -1)
        self.title_lab.SetFont(font)

        m3u8_link_lab = wx.StaticText(self, -1, "m3u8 链接")
        self.m3u8_link_box = wx.TextCtrl(self, -1, size = self.FromDIP((350, -1)))
        self.copy_link_btn = wx.Button(self, -1, "复制")

        recording_lab = wx.StaticText(self, -1, "保存位置")
        self.recording_path_box = wx.TextCtrl(self, -1, size = self.FromDIP((350, -1)))
        self.browse_path_btn = wx.Button(self, -1, "浏览")

        bag_box = wx.GridBagSizer(2, 3)
        bag_box.Add(m3u8_link_lab, pos = (0, 0), flag = wx.ALL | wx.ALIGN_CENTER, border = 10)
        bag_box.Add(self.m3u8_link_box, pos = (0, 1), flag = wx.ALL & (~wx.LEFT), border = 10)
        bag_box.Add(self.copy_link_btn, pos = (0, 2), flag = wx.ALL & (~wx.LEFT), border = 10)
        bag_box.Add(recording_lab, pos = (1, 0), flag = wx.ALL | wx.ALIGN_CENTER, border = 10)
        bag_box.Add(self.recording_path_box, pos = (1, 1), flag = wx.ALL & (~wx.LEFT), border = 10)
        bag_box.Add(self.browse_path_btn, pos = (1, 2), flag = wx.ALL & (~wx.LEFT), border = 10)

        self.start_recording_btn = wx.Button(self, -1, "开始录制", size = self.FromDIP((100, 28)))
        self.open_player = wx.Button(self, -1, "直接播放", size = self.FromDIP((100, 28)))

        action_hbox = wx.BoxSizer(wx.HORIZONTAL)
        action_hbox.AddStretchSpacer()
        action_hbox.Add(self.open_player, 0, wx.ALL, 10)
        action_hbox.Add(self.start_recording_btn, 0, wx.ALL & (~wx.LEFT), 10)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.title_lab, 0, wx.ALL, 10)
        vbox.Add(bag_box)
        vbox.Add(action_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def init_live_info(self):
        self.title_lab.SetLabel(LiveInfo.title)

        self.m3u8_link_box.SetValue(LiveInfo.m3u8_link)
