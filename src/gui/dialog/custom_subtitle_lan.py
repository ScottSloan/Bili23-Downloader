import wx
import json

from utils.tool_v2 import RequestTool
from utils.common.thread import Thread

from gui.component.dialog import Dialog

class CustomLanDialog(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent, "自定义字幕语言")

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

        self.CenterOnParent()

    def init_UI(self):
        lan_lab = wx.StaticText(self, -1, "字幕语言下载选项")
        self.select_all_radio = wx.RadioButton(self, -1, "自动下载全部可用的字幕")
        self.custom_radio = wx.RadioButton(self, -1, "手动选择")

        self.lan_box = wx.CheckListBox(self, -1, size = self.FromDIP((200, 150)))

        self.ok_btn = wx.Button(self, wx.ID_OK, "确定", size = self.get_scaled_size((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, "取消", size = self.get_scaled_size((80, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(self.ok_btn, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        bottom_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(lan_lab, 0, wx.ALL, self.FromDIP(6))
        vbox.Add(self.select_all_radio, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        vbox.Add(self.custom_radio, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        vbox.Add(self.lan_box, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def init_utils(self):
        def worker():
            self.get_lan_list()

            wx.CallAfter(self.lan_box.Set, list(self.lan_list.keys()))

        self.onChangeOptionEVT(0)

        Thread(target = worker).start()

    def Bind_EVT(self):
        self.select_all_radio.Bind(wx.EVT_RADIOBUTTON, self.onChangeOptionEVT)
        self.custom_radio.Bind(wx.EVT_RADIOBUTTON, self.onChangeOptionEVT)

    def onChangeOptionEVT(self, event):
        enable = self.custom_radio.GetValue()

        self.lan_box.Enable(enable)

    def get_lan_list(self):
        url = "https://i0.hdslb.com/bfs/subtitle/subtitle_lan.json"

        req = RequestTool.request_get(url)
        data = json.loads(req.text)

        self.lan_list = {entry["doc_zh"]: entry["lan"] for entry in data}

