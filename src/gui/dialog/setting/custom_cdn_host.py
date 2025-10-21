import wx
import gettext

from utils.config import Config
from utils.common.thread import ThreadPoolExecutor

from utils.module.web.ping import Ping

from gui.component.window.dialog import Dialog

_ = gettext.gettext

class CustomCDNDialog(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent, _("自定义 CDN 节点"))

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

        self.CenterOnParent()

    def init_UI(self):
        cdn_lab = wx.StaticText(self, -1, _("CDN 节点列表"))

        self.cdn_list = wx.ListCtrl(self, -1, size = self.FromDIP((670, 250)), style = wx.LC_REPORT | wx.LC_SINGLE_SEL)

        custom_lab = wx.StaticText(self, -1, _("自定义"))
        self.custom_box = wx.TextCtrl(self, -1, size = self.FromDIP((240, -1)))
        self.add_btn = wx.Button(self, -1, _("添加"), size = self.get_scaled_size((80, 28)))
        self.delete_btn = wx.Button(self, -1, _("删除"), size = self.get_scaled_size((80, 28)))
        self.up_btn = wx.Button(self, -1, "↑", size = self.get_scaled_size((28, 28)))
        self.down_btn = wx.Button(self, -1, "↓", size = self.get_scaled_size((28, 28)))

        self.ping_btn = wx.Button(self, -1, _("Ping 测试"), size = self.get_scaled_size((100, 28)))

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

        self.ok_btn = wx.Button(self, wx.ID_OK, _("确定"), size = self.get_scaled_size((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, _("取消"), size = self.get_scaled_size((80, 30)))

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

    def init_utils(self):
        def init_listctrl():
            self.cdn_list.AppendColumn(_("优先级"), width = self.FromDIP(75))
            self.cdn_list.AppendColumn(_("CDN 节点"), width = self.FromDIP(360))
            self.cdn_list.AppendColumn(_("延迟"), width = self.FromDIP(100))

        def init_cdn_list():
            for cdn in Config.Temp.cdn_list:
                self.cdn_list.Append(["", cdn, _("未检测")])

            self.update_priority()

        init_listctrl()
        init_cdn_list()

    def onOKEVT(self):
        if self.cdn_list.GetItemCount() == 0:
            wx.MessageDialog(self, _("保存失败\n\n至少需要添加一个 CDN 节点"), _("警告"), wx.ICON_WARNING).ShowModal()
            return
        
        Config.Temp.cdn_list = [self.cdn_list.GetItemText(i, 0) for i in range(self.cdn_list.GetItemCount())]
    
    def onPingTestEVT(self, event):
        def worker(index: int, cdn: str):
            def update(value):
                self.cdn_list.SetItem(index, 2, value)

            wx.CallAfter(update, _("正在检测..."))

            result = Ping.run(cdn)

            wx.CallAfter(update, result)

        thread_pool = ThreadPoolExecutor(max_workers = 5)

        for i in range(self.cdn_list.GetItemCount()):
            item: wx.ListItem = self.cdn_list.GetItem(i, 1)

            thread_pool.submit(worker, i, item.GetText())

    def onAddEVT(self, event):
        if not self.custom_box.GetValue():
            wx.MessageDialog(self, _("添加失败\n\n请输入要添加的 CDN 节点"), _("警告"), wx.ICON_WARNING).ShowModal()
            self.custom_box.SetFocus()
            return

        for i in range(self.cdn_list.GetItemCount()):
            if self.cdn_list.GetItemText(i, 1) == self.custom_box.GetValue():
                wx.MessageDialog(self, _("添加失败\n\n无法重复添加已存在的项目"), _("警告"), wx.ICON_WARNING).ShowModal()
                self.custom_box.SetFocus()
                return

        index = self.cdn_list.Append([str(self.cdn_list.GetItemCount() + 1), self.custom_box.GetValue(), _("未检测")])

        self.cdn_list.Select(index)
        self.cdn_list.Focus(index)

    def onDeleteEVT(self, event):
        if self.check_item_focused():
            return

        dlg = wx.MessageDialog(self, _("删除项目\n\n确定要删除选定的项目吗？"), _("警告"), wx.ICON_WARNING | wx.YES_NO)

        if dlg.ShowModal() == wx.ID_YES:
            self.cdn_list.DeleteItem(self.cdn_list.GetFocusedItem())

    def onUpEVT(self, event):
        if self.check_item_focused():
            return
        
        self.move_to(self.cdn_list.GetFocusedItem() - 1)

    def onDownEVT(self, event):   
        if self.check_item_focused():
            return
             
        self.move_to(self.cdn_list.GetFocusedItem() + 1)

    def move_to(self, index: int):
        current_item = self.cdn_list.GetFocusedItem()

        if index in range(0, self.cdn_list.GetItemCount()):
            label = self.cdn_list.GetItemText(current_item, 1)
            latency = self.cdn_list.GetItemText(current_item, 2)

            self.cdn_list.DeleteItem(current_item)
            self.cdn_list.InsertItem(index, "")

            self.cdn_list.SetItem(index, 1, label)
            self.cdn_list.SetItem(index, 2, latency)

            self.cdn_list.Select(index)
            self.cdn_list.Focus(index)
        else:
            wx.Bell()

        self.cdn_list.SetFocus()

        self.update_priority()

    def update_priority(self):
        for index in range(self.cdn_list.GetItemCount()):
            self.cdn_list.SetItem(index, 0, str(index + 1))

    def check_item_focused(self):
        if self.cdn_list.GetFocusedItem() == -1:
            wx.MessageDialog(self, _("未选择项目\n\n请选择要调整的项目"), _("警告"), wx.ICON_WARNING).ShowModal()
            return True
