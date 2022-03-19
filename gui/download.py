import wx

from gui.template import Dialog

class DownloadWindow(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent, "准备下载", (500, 135))
     
        self.init_controls()

    def init_controls(self):
        self.lb = wx.StaticText(self.panel, -1, "获取下载地址中...")

        self.gauge = wx.Gauge(self.panel, -1, 100, style = wx.GA_SMOOTH)
        self.gauge.Pulse()
        self.progress_lb = wx.StaticText(self.panel, -1, "--%")

        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        hbox1.Add(self.gauge, 1, wx.EXPAND | wx.ALL & (~wx.TOP), 10)
        hbox1.Add(self.progress_lb, 0, wx.ALIGN_CENTER | wx.RIGHT | wx.BOTTOM, 10)

        self.speed_lb = wx.StaticText(self.panel, -1, "速度：-")
        self.size_lb = wx.StaticText(self.panel, -1, "大小：-")

        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        hbox2.Add(self.speed_lb, 1, wx.LEFT | wx.BOTTOM, 10)
        hbox2.Add(self.size_lb, 1, wx.LEFT | wx.BOTTOM, 10)

        vbox = wx.BoxSizer(wx.VERTICAL)

        vbox.Add(self.lb, 0, wx.ALL, 10)
        vbox.Add(hbox1, 0, wx.EXPAND)
        vbox.Add(hbox2, 1, wx.EXPAND)

        self.panel.SetSizer(vbox)

    def on_download_start(self, size: str, index: list, file_name: str, title: str):
        self.SetTitle("当前第 {} 个，共 {} 个".format(index[0], index[1]))

        down_type = "视频" if file_name.endswith("mp4") else "音频"
        self.lb.SetLabel("正在下载{}：{}".format(down_type, title))
        self.size_lb.SetLabel("大小：{}".format(size))

    def on_downloading(self, progress: int, speed: str):
        self.gauge.SetValue(progress)
        self.progress_lb.SetLabel("{}%".format(progress))

        self.speed_lb.SetLabel("速度：{}".format(speed))

    def on_merge(self):
        self.gauge.Pulse()
        self.lb.SetLabel("正在合成视频......")

        self.progress_lb.SetLabel("--%")
        self.speed_lb.SetLabel("速度：-")
        self.size_lb.SetLabel("大小：-")