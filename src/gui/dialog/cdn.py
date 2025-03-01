import re
import wx
import subprocess
from concurrent.futures import ThreadPoolExecutor

from utils.config import Config
from utils.common.map import cdn_map

from gui.templates import TextCtrl

class ChangeCDNDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, "更改 CDN host")

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

        cdn_lab = wx.StaticText(self, -1, "CDN host 列表")

        self.cdn_list = wx.ListCtrl(self, -1, size = self.FromDIP((650, 250)), style = wx.LC_REPORT | wx.LC_SINGLE_SEL)
        self.cdn_list.EnableCheckBoxes(True)

        custom_lab = wx.StaticText(self, -1, "自定义")
        self.custom_box = TextCtrl(self, -1, size = _get_scale_size((240, 24)))
        self.add_btn = wx.Button(self, -1, "添加", size = _get_scale_size((80, 28)))
        self.delete_btn = wx.Button(self, -1, "删除", size = _get_scale_size((80, 28)))

        self.ping_btn = wx.Button(self, -1, "Ping 测试", size = _get_scale_size((100, 28)))

        action_hbox = wx.BoxSizer(wx.HORIZONTAL)
        action_hbox.Add(custom_lab, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM) | wx.ALIGN_CENTER, 10)
        action_hbox.Add(self.custom_box, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM) & (~wx.LEFT) | wx.ALIGN_CENTER, 10)
        action_hbox.Add(self.add_btn, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM) & (~wx.LEFT), 10)
        action_hbox.Add(self.delete_btn, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM) & (~wx.LEFT), 10)
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
        self.add_btn.Bind(wx.EVT_BUTTON, self.onAddCDNEVT)
        self.delete_btn.Bind(wx.EVT_BUTTON, self.onDeleteCDNEVT)
        self.ok_btn.Bind(wx.EVT_BUTTON, self.onConfirm)

    def init_utils(self):
        def init_listctrl():
            self.cdn_list.AppendColumn("序号", width = self.FromDIP(75))
            self.cdn_list.AppendColumn("CDN host", width = self.FromDIP(280))
            self.cdn_list.AppendColumn("提供商", width = self.FromDIP(140))
            self.cdn_list.AppendColumn("延迟", width = self.FromDIP(100))

        def init_cdn_list():
            for key, value in cdn_map.items():
                index = self.cdn_list.Append([str(key + 1), value["cdn"], value["provider"], "未知"])

                if value["cdn"] == Config.Advanced.custom_cdn:
                    self.cdn_list.CheckItem(index)

            self.update_index()

        self._last_index = -1

        init_listctrl()
        init_cdn_list()

    def get_cdn(self):
        return self.cdn_list.GetItemText(self._last_index, 1)

    def onConfirm(self, event):
        if self._last_index == -1 or not self.cdn_list.IsItemChecked(self._last_index):
            wx.MessageDialog(self, "更改失败\n\n请选择需要更改的 CDN", "警告", wx.ICON_WARNING).ShowModal()
            return

        event.Skip()
    
    def onPingTestEVT(self, event):
        def worker(index: int, cdn: str):
            def update(value):
                self.cdn_list.SetItem(index, 3, value)
            
            def get_ping_cmd() -> str:
                match Config.Sys.platform:
                    case "windows":
                        return f"ping {cdn}"
                    
                    case "linux" | "darwin":
                        return f"ping {cdn} -c 4"

            def get_latency():
                match Config.Sys.platform:
                    case "windows":
                        return re.findall(r"Average = ([0-9]*)", process.stdout)
                    
                    case "linux" | "darwin":
                        _temp = re.findall(r"time=([0-9]*)", process.stdout)

                        if _temp:
                            return [int(sum(list(map(int, _temp))) / len(_temp))]
                        else:
                            return None
                    
            wx.CallAfter(update, "正在检测...")

            process = subprocess.run(get_ping_cmd(), stdout = subprocess.PIPE, stderr = subprocess.STDOUT, shell = True, text = True, encoding = "utf-8")
            latency = get_latency()

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

    def onAddCDNEVT(self, event):
        if not self.custom_box.GetValue():
            wx.MessageDialog(self, "添加失败\n\n请输入要添加的 CDN", "警告", wx.ICON_WARNING).ShowModal()
            self.custom_box.SetFocus()
            return

        for i in range(self.cdn_list.GetItemCount()):
            item: wx.ListItem = self.cdn_list.GetItem(i, 1)

            if item.GetText() == self.custom_box.GetValue():
                wx.MessageDialog(self, "添加失败\n\n已存在相同的 CDN，无法重复添加", "警告", wx.ICON_WARNING).ShowModal()
                self.custom_box.SetFocus()
                return
            
        self.cdn_list.SetFocus()
        
        index = self.cdn_list.Append(["-", self.custom_box.GetValue(), "自定义", "未知"])

        Config.Advanced.custom_cdn_list.append(self.custom_box.GetValue())

        self.cdn_list.Focus(index)
        self.cdn_list.Select(index)

        self.update_index()
    
    def onDeleteCDNEVT(self, event):
        if self._last_index == -1 or not self.cdn_list.IsItemChecked(self._last_index):
            wx.MessageDialog(self, "删除失败\n\n请选择要删除的 CDN", "警告", wx.ICON_WARNING).ShowModal()
            self.cdn_list.SetFocus()
            return
        
        cdn = self.cdn_list.GetItemText(self._last_index, 1)
        
        if self.cdn_list.GetItemText(self._last_index, 2) != "自定义":
            wx.MessageDialog(self, "删除失败\n\n仅支持删除自定义的 CDN", "警告", wx.ICON_WARNING).ShowModal()
            self.cdn_list.SetFocus()
            return

        self.cdn_list.DeleteItem(self._last_index)

        Config.Advanced.custom_cdn_list.remove(cdn)

        self._last_index = -1

        self.update_index()

    def update_index(self):
        for i in range(self.cdn_list.GetItemCount()):
            self.cdn_list.SetItem(i, 0, str(i + 1))