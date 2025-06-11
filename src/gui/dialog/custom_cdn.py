import wx

from utils.config import Config
from utils.common.thread import ThreadPoolExecutor

from utils.module.ping import Ping

from gui.component.text_ctrl import TextCtrl
from gui.component.dialog import Dialog

class CustomCDNDialog(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent, "自定义 CDN 节点")

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

        self.CenterOnParent()

    def init_UI(self):
        cdn_lab = wx.StaticText(self, -1, "CDN 节点列表")

        self.cdn_list = wx.ListCtrl(self, -1, size = self.FromDIP((670, 250)), style = wx.LC_REPORT | wx.LC_SINGLE_SEL)

        custom_lab = wx.StaticText(self, -1, "自定义")
        self.custom_box = TextCtrl(self, -1, size = self.get_scaled_size((240, 24)))
        self.add_btn = wx.Button(self, -1, "添加", size = self.get_scaled_size((80, 28)))
        self.delete_btn = wx.Button(self, -1, "删除", size = self.get_scaled_size((80, 28)))
        self.up_btn = wx.Button(self, -1, "↑", size = self.get_scaled_size((28, 28)))
        self.down_btn = wx.Button(self, -1, "↓", size = self.get_scaled_size((28, 28)))

        self.ping_btn = wx.Button(self, -1, "Ping 测试", size = self.get_scaled_size((100, 28)))

        action_hbox = wx.BoxSizer(wx.HORIZONTAL)
        action_hbox.Add(custom_lab, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM) | wx.ALIGN_CENTER, self.FromDIP(6))
        action_hbox.Add(self.custom_box, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM) & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        action_hbox.Add(self.add_btn, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM) & (~wx.LEFT), self.FromDIP(6))
        action_hbox.Add(self.delete_btn, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM) & (~wx.LEFT), self.FromDIP(6))
        action_hbox.Add(self.up_btn, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM) & (~wx.LEFT), self.FromDIP(6))
        action_hbox.Add(self.down_btn, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM) & (~wx.LEFT), self.FromDIP(6))
        action_hbox.AddStretchSpacer()
        action_hbox.Add(self.ping_btn, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM), self.FromDIP(6))

        bottom_line = wx.StaticLine(self, -1)

        self.ok_btn = wx.Button(self, wx.ID_OK, "确定", size = self.get_scaled_size((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, "取消", size = self.get_scaled_size((80, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer(1)
        bottom_hbox.Add(self.ok_btn, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        bottom_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(cdn_lab, 0, wx.ALL & (~wx.BOTTOM), self.FromDIP(6))
        vbox.Add(self.cdn_list, 0, wx.ALL | wx.EXPAND, self.FromDIP(6))
        vbox.Add(action_hbox, 0, wx.EXPAND)
        vbox.Add(bottom_line, 0, wx.ALL | wx.EXPAND, self.FromDIP(6))
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def Bind_EVT(self):
        self.ping_btn.Bind(wx.EVT_BUTTON, self.onPingTestEVT)

        self.add_btn.Bind(wx.EVT_BUTTON, self.onAddEVT)
        self.delete_btn.Bind(wx.EVT_BUTTON, self.onDeleteEVT)
        self.up_btn.Bind(wx.EVT_BUTTON, self.onUpEVT)
        self.down_btn.Bind(wx.EVT_BUTTON, self.onDownEVT)

        self.ok_btn.Bind(wx.EVT_BUTTON, self.onConfirm)

    def init_utils(self):
        def init_listctrl():
            self.cdn_list.AppendColumn("CDN 节点", width = self.FromDIP(350))
            self.cdn_list.AppendColumn("优先级", width = self.FromDIP(120))
            self.cdn_list.AppendColumn("延迟", width = self.FromDIP(100))

        def init_cdn_list():
            for cdn in Config.Temp.cdn_list:
                self.cdn_list.Append([cdn, "", "未检测"])

            self.setItemOrder()

        init_listctrl()
        init_cdn_list()

    def onConfirm(self, event):
        if self.cdn_list.GetItemCount() == 0:
            wx.MessageDialog(self, "保存失败\n\n至少需要添加一个 CDN 节点", "警告", wx.ICON_WARNING).ShowModal()
            return
        
        Config.Temp.cdn_list = [self.cdn_list.GetItemText(i, 0) for i in range(self.cdn_list.GetItemCount())]

        event.Skip()
    
    def onPingTestEVT(self, event):
        def worker(index: int, cdn: str):
            def update(value):
                self.cdn_list.SetItem(index, 2, value)
            
            wx.CallAfter(update, "正在检测...")

            result = Ping.run(cdn)

            wx.CallAfter(update, result)

        thread_pool = ThreadPoolExecutor(max_workers = 5)

        for i in range(self.cdn_list.GetItemCount()):
            item: wx.ListItem = self.cdn_list.GetItem(i, 0)

            thread_pool.submit(worker, i, item.GetText())

    def onAddEVT(self, event):
        if not self.custom_box.GetValue():
            wx.MessageDialog(self, "添加失败\n\n请输入要添加的 CDN", "警告", wx.ICON_WARNING).ShowModal()
            self.custom_box.SetFocus()
            return

        for i in range(self.cdn_list.GetItemCount()):
            if self.cdn_list.GetItemText(i, 0) == self.custom_box.GetValue():
                wx.MessageDialog(self, "添加失败\n\n无法重复添加已存在的项目", "警告", wx.ICON_WARNING).ShowModal()
                self.custom_box.SetFocus()
                return
                    
        index = self.cdn_list.Append([self.custom_box.GetValue(), "", "未检测"])

        self.setItemOrder()

        self.cdn_list.Select(index)
        self.cdn_list.Focus(index)

    def onDeleteEVT(self, event):
        dlg = wx.MessageDialog(self, "删除项目\n\n确定要删除选定的项目吗？", "警告", wx.ICON_WARNING | wx.YES_NO)

        if dlg.ShowModal() == wx.ID_YES:
            self.cdn_list.DeleteItem(self.cdn_list.GetFocusedItem())

    def onUpEVT(self, event):
        current_item = self.cdn_list.GetFocusedItem()

        if current_item > 0:
            previous_item = current_item - 1

            host = self.cdn_list.GetItemText(previous_item, 0)
            latency = self.cdn_list.GetItemText(previous_item, 2)

            self.cdn_list.DeleteItem(previous_item)
            self.cdn_list.InsertItem(current_item, "")

            self.cdn_list.SetItem(current_item, 0, host)
            self.cdn_list.SetItem(current_item, 2, latency)

            self.setItemOrder()

            self.cdn_list.Select(previous_item)
            self.cdn_list.Focus(previous_item)

    def onDownEVT(self, event):
        current_item = self.cdn_list.GetFocusedItem()
        
        if current_item < self.cdn_list.GetItemCount() - 1:
            next_item = current_item + 1

            host = self.cdn_list.GetItemText(next_item, 0)
            latency = self.cdn_list.GetItemText(next_item, 2)

            self.cdn_list.DeleteItem(next_item)
            self.cdn_list.InsertItem(current_item, "")

            self.cdn_list.SetItem(current_item, 0, host)
            self.cdn_list.SetItem(current_item, 2, latency)

            self.setItemOrder()

            self.cdn_list.Select(next_item)
            self.cdn_list.Focus(next_item)

    def setItemOrder(self):
        for index in range(self.cdn_list.GetItemCount()):
            self.cdn_list.SetItem(index, 1, str(index + 1))
