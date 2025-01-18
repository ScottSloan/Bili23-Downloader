import re
import wx
import subprocess
from concurrent.futures import ThreadPoolExecutor

from utils.config import Config
from utils.common.map import cdn_map

class ChangeCDNDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, "更改 CDN")

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

        self.CenterOnParent()

    def init_UI(self):
        def _get_scale_size(_size: tuple):
            match Config.Sys.platform:
                case "windows":
                    return self.FromDIP(_size)
                
                case "linux" | "darwin":
                    return wx.DefaultSize

        cdn_lab = wx.StaticText(self, -1, "CDN 列表")

        self.cdn_list = wx.ListCtrl(self, -1, size = self.FromDIP((650, 250)), style = wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.cdn_list.EnableCheckBoxes(True)

        self.ping_btn = wx.Button(self, -1, "Ping 测试", size = _get_scale_size((100, 28)))

        action_hbox = wx.BoxSizer(wx.HORIZONTAL)
        action_hbox.AddStretchSpacer()
        action_hbox.Add(self.ping_btn, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM), 10)

        bottom_line = wx.StaticLine(self, -1)

        self.ok_btn = wx.Button(self, wx.ID_OK, "确定", size = _get_scale_size((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, "取消", size = _get_scale_size((80, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer(1)
        bottom_hbox.Add(self.ok_btn, 0, wx.ALL & (~wx.TOP), 10)
        bottom_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), 10)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(cdn_lab, 0, wx.ALL & (~wx.BOTTOM), 10)
        vbox.Add(self.cdn_list, 0, wx.ALL | wx.EXPAND, 10)
        vbox.Add(action_hbox, 0, wx.EXPAND)
        vbox.Add(bottom_line, 0, wx.ALL | wx.EXPAND, 10)
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def Bind_EVT(self):
        self.cdn_list.Bind(wx.EVT_LIST_ITEM_CHECKED, self.onCheckEVT)
        self.cdn_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.onItemActivateEVT)

        self.ping_btn.Bind(wx.EVT_BUTTON, self.onPingTestEVT)
        self.ok_btn.Bind(wx.EVT_BUTTON, self.onConfirm)

    def init_utils(self):
        def init_listctrl():
            self.cdn_list.AppendColumn("序号", width = self.FromDIP(50))
            self.cdn_list.AppendColumn("CDN", width = self.FromDIP(280))
            self.cdn_list.AppendColumn("提供商", width = self.FromDIP(140))
            self.cdn_list.AppendColumn("延迟", width = self.FromDIP(100))

        def init_cdn_list():
            for key, value in cdn_map.items():
                self.cdn_list.Append([str(key + 1), value["cdn"], value["provider"], "未知"])

        init_listctrl()
        init_cdn_list()

        self._last_index = -1

    def get_cdn(self):
        return self.cdn_list.GetItemText(self._last_index, 1)

    def onConfirm(self, event):
        if self._last_index == -1 or not self.cdn_list.IsItemChecked(self._last_index):
            wx.MessageDialog(self, "请选择 CDN\n\n请选择需要替换的 CDN", "警告", wx.ICON_WARNING).ShowModal()
            return

        event.Skip()
    
    def onPingTestEVT(self, event):
        def worker(index: int, cdn: str):
            def update(value):
                self.cdn_list.SetItem(index, 3, value)
            
            wx.CallAfter(update, "正在检测...")

            process = subprocess.run(f"ping {cdn}", stdout = subprocess.PIPE, stderr = subprocess.STDOUT, shell = True, text = True, encoding = "utf-8")
            latency = re.findall(r"Average = ([0-9]*)", process.stdout)

            if latency:
                result = f"{latency[0]}ms"
            else:
                result = "请求超时"

            wx.CallAfter(update, result)

        thread_pool = ThreadPoolExecutor(max_workers = 5)

        for i in range(self.cdn_list.GetItemCount()):
            item: wx.ListItem = self.cdn_list.GetItem(i, 1)

            thread_pool.submit(worker, i, item.GetText())
    
    def onCheckEVT(self, event: wx.ListEvent):
        index = event.GetIndex()

        if self._last_index != -1 and self._last_index != index:
            self.cdn_list.CheckItem(self._last_index, False)

        self.cdn_list.Select(index)

        self._last_index = index

    def onItemActivateEVT(self, event: wx.ListEvent):
        index = event.GetIndex()

        self.cdn_list.CheckItem(index)