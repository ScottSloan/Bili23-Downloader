import wx

from .templates import Frame
from .download import DownloadWindow

class DebugWindow(Frame):
    def __init__(self, parent):
        Frame.__init__(self, parent, "Debug")

        self.init_UI()

        self.Bind_EVT()

        self.CenterOnParent()

    def init_UI(self):
        self.hbox = wx.BoxSizer(wx.HORIZONTAL)
        self.vbox = wx.BoxSizer(wx.VERTICAL)

        self.hbox.Add(self.vbox, 0, wx.EXPAND)

        self.init_info_UI()
        self.init_download_UI()
        self.init_list_UI()

        self.init_video_info()
        self.init_list_box()
        
        self.panel.SetSizer(self.hbox)

        self.hbox.Fit(self)

    def init_info_UI(self):
        info_box = wx.StaticBox(self.panel, -1, "视频信息")

        self.video_title_lab = wx.StaticText(self.panel, -1, "视频名称：")
        self.video_url_lab = wx.StaticText(self.panel, -1, "URL：")
        self.video_bvid_lab = wx.StaticText(self.panel, -1, "BV：")
        self.video_cid_lab = wx.StaticText(self.panel, -1, "cid：")
        
        self.refresh_btn = wx.Button(self.panel, -1, "刷新", size = self.FromDIP((90, 30)))

        self.info_sbox = wx.StaticBoxSizer(info_box, wx.VERTICAL)

        self.info_sbox.Add(self.video_title_lab, 0, wx.ALL, 10)
        self.info_sbox.Add(self.video_url_lab, 0, wx.ALL & ~(wx.TOP), 10)
        self.info_sbox.Add(self.video_bvid_lab, 0, wx.ALL & ~(wx.TOP), 10)
        self.info_sbox.Add(self.video_cid_lab, 0, wx.ALL & ~(wx.TOP), 10)
        self.info_sbox.Add(self.refresh_btn, 0, wx.ALL & ~(wx.TOP), 10)

        self.vbox.Add(self.info_sbox, 0, wx.ALL | wx.EXPAND, 10)

    def init_download_UI(self):
        download_box = wx.StaticBox(self.panel, -1, "下载")

        
        title_lab = wx.StaticText(self.panel, -1, "标题")
        self.title_box= wx.TextCtrl(self.panel, -1)

        title_hbox = wx.BoxSizer(wx.HORIZONTAL)

        title_hbox.Add(title_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        title_hbox.Add(self.title_box, 1, wx.ALL & ~(wx.LEFT), 10)

        
        bv_lab = wx.StaticText(self.panel, -1, "BV")
        self.bv_box= wx.TextCtrl(self.panel, -1, "BV84520")

        bv_hbox = wx.BoxSizer(wx.HORIZONTAL)

        bv_hbox.Add(bv_lab, 0, wx.ALL & ~(wx.TOP) | wx.ALIGN_CENTER, 10)
        bv_hbox.Add(self.bv_box, 1, wx.ALL & ~(wx.LEFT) & ~(wx.TOP), 10)

        
        cid_lab = wx.StaticText(self.panel, -1, "cid")
        self.cid_box= wx.TextCtrl(self.panel, -1, "84520")

        cid_hbox = wx.BoxSizer(wx.HORIZONTAL)

        cid_hbox.Add(cid_lab, 0, wx.ALL & ~(wx.TOP) | wx.ALIGN_CENTER, 10)
        cid_hbox.Add(self.cid_box, 1, wx.ALL & ~(wx.LEFT) & ~(wx.TOP), 10)

        self.open_btn = wx.Button(self.panel, -1, "打开下载管理", size = self.FromDIP((100, 30)))
        self.add_btn = wx.Button(self.panel, -1, "添加至下载列表", size = self.FromDIP((100, 30)))

        btn_hbox = wx.BoxSizer(wx.HORIZONTAL)

        btn_hbox.Add(self.open_btn, 0, wx.ALL & ~(wx.TOP), 10)
        btn_hbox.AddStretchSpacer()
        btn_hbox.Add(self.add_btn, 0, wx.ALL & ~(wx.LEFT) & ~(wx.TOP), 10)

        download_sbox = wx.StaticBoxSizer(download_box, wx.VERTICAL)
        download_sbox.Add(title_hbox, 0, wx.EXPAND)
        download_sbox.Add(bv_hbox, 0, wx.EXPAND)
        download_sbox.Add(cid_hbox, 0, wx.EXPAND)
        download_sbox.Add(btn_hbox, 0, wx.EXPAND)
        
        self.vbox.Add(download_sbox, 0, wx.ALL & ~(wx.TOP) | wx.EXPAND, 10)
    
    def init_list_UI(self):
        list_box = wx.StaticBox(self.panel, -1, " 下载列表")
        
        self.list_box = wx.ListCtrl(self.panel, -1, style = wx.LC_REPORT)

        list_sbox = wx.StaticBoxSizer(list_box, wx.VERTICAL)

        list_sbox.Add(self.list_box, 0, wx.ALL, 10)

        self.hbox.Add(list_sbox, 0, wx.EXPAND | wx.ALL, 10)

    def Bind_EVT(self):
        self.open_btn.Bind(wx.EVT_BUTTON, self.open_btn_EVT)
        self.add_btn.Bind(wx.EVT_BUTTON, self.add_btn_EVT)

        self.refresh_btn.Bind(wx.EVT_BUTTON, self.refresh_btn_EVT)

    def init_video_info(self):
        if not hasattr(self.Parent, "type"):
            return

        type = self.Parent.type

        self.video_title_lab.SetLabel("视频名称：" + type.title)
        self.video_url_lab.SetLabel("URL：" + type.url)
        self.video_bvid_lab.SetLabel("BV：" + type.bvid)
        self.video_cid_lab.SetLabel("cid：{}".format(type.cid))

    def init_list_box(self):
        self.list_box.ClearAll()

        self.list_box.InsertColumn(0, "ID", width = self.FromDIP(35))
        self.list_box.InsertColumn(1, "标题", width = self.FromDIP(100))
        self.list_box.InsertColumn(2, "状态", width = self.FromDIP(50))

    def open_btn_EVT(self, event):
        self.download_window = DownloadWindow(self.Parent)
        self.download_window.Show()

    def add_btn_EVT(self, event):
        info = {
            "id": "1",
            "url": "https://bilibili.com/video/" + self.bv_box.GetValue(),
            "title": self.title_box.GetValue(),
            "bvid": self.bv_box.GetValue(),
            "cid": int(self.cid_box.GetValue()),
            "quality_id": 80,
            "type": "video"
        }

        self.download_window.list_panel.download_list_panel.add_panel([info])

    def refresh_btn_EVT(self, event):
        self.init_video_info()

        self.info_sbox.Layout()
        
        self.vbox.Fit(self)