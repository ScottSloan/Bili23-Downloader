import wx
from typing import Callable

from gui.component.panel.scrolled_panel import ScrolledPanel
from gui.component.panel.panel import Panel

class EmptyItemPanel(Panel):
    def __init__(self, parent, label: str, name: str):
        self.label = label

        Panel.__init__(self, parent, name = name)

        self.init_UI()

    def init_UI(self):
        self.set_dark_mode()

        self.empty_lab = wx.StaticText(self, -1, self.label)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.AddStretchSpacer()
        hbox.Add(self.empty_lab, 0, wx.ALL, self.FromDIP(6))
        hbox.AddStretchSpacer()

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.AddStretchSpacer()
        vbox.Add(hbox, 0, wx.EXPAND)
        vbox.AddStretchSpacer()

        self.SetSizer(vbox)

    def destroy_panel(self):
        self.Destroy()

class LoadMoreTaskItemPanel(Panel):
    def __init__(self, parent, left_count: int, load_more_callback: Callable, name: str):
        self.count, self.callback = left_count, load_more_callback

        Panel.__init__(self, parent, name = name)

        self.init_UI()

        self.Bind_EVT()

    def init_UI(self):
        self.set_dark_mode()

        self.more_lab = wx.StaticText(self, -1, f"显示更多项目({self.count}+)")
        self.more_lab.SetCursor(wx.Cursor(wx.Cursor(wx.CURSOR_HAND)))
        
        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.AddStretchSpacer()
        hbox.Add(self.more_lab, 0, wx.ALL, self.FromDIP(6))
        hbox.AddStretchSpacer()

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(hbox, 0, wx.EXPAND)

        self.SetSizer(vbox)
    
    def Bind_EVT(self):
        self.more_lab.Bind(wx.EVT_LEFT_DOWN, self.onShowMoreEVT)

    def onShowMoreEVT(self, event):
        wx.BeginBusyCursor()
        self.more_lab.SetLabel("正在加载...")
        self.GetSizer().Layout()

        self.callback()

        wx.EndBusyCursor()

    def destroy_panel(self):
        self.Destroy()

class ScrolledPanelList(ScrolledPanel):
    def __init__(self, parent, info: dict):
        self.info = info

        ScrolledPanel.__init__(self, parent)

        self.SetDoubleBuffered(True)

        self.init_utils()

    def init_utils(self):
        self.more = False
        self.info_list = []

        self.max_items = self.info.get("max_items", 25)
        self.add_panel_item: Callable = self.info.get("add_panel_item")
        self.load_more_item: Callable = self.info.get("load_more_item")

        self.add_empty_panel()

    def ShowListItems(self, after_show_items_callback: Callable = None, load_items: int = None, max_limit: bool = False):
        panel_list = self.add_panel_item(self.get_items_batch(load_items, max_limit))

        self.Freeze()

        if panel_list:
            self.remove_empty_panel()

            self.remove_more_panel()

            self.sizer.AddMany(panel_list)

        if len(self.info_list):
            self.remove_more_panel()

            self.add_more_panel()

        self.Layout()

        self.Thaw()

        if after_show_items_callback:
            after_show_items_callback()
    
    def get_items_batch(self, load_items: int = None, max_limit: bool = False):
        if max_limit:
            count = max(self.max_items - self.get_items_count(), 0)
        else:
            count = load_items if load_items else self.max_items

        temp_items = self.info_list[:count]
        del self.info_list[:count]

        return temp_items

    def Add(self, window: wx.Window, proportion: int = 0, flag: int = 0, border: int = 0):
        self.remove_empty_panel()

        self.sizer.Add(window, proportion, flag, border)

        self.Layout()

    def AddMany(self, items):
        self.remove_empty_panel()

        self.sizer.AddMany(items)

        self.Layout()

    def add_empty_panel(self):
        self.empty = True

        empty_item = EmptyItemPanel(self, self.info.get("empty_label"), "empty_panel")

        self.Add(empty_item, 1, wx.EXPAND)

    def remove_empty_panel(self):
        if self.empty and not self.sizer.IsEmpty():
            empty_panel: EmptyItemPanel = wx.FindWindowByName("empty_panel", self)

            if empty_panel:
                empty_panel.destroy_panel()

            self.empty = False

    def add_more_panel(self):
        self.more = True

        more_item = LoadMoreTaskItemPanel(self, len(self.info_list), self.load_more_item, "more_panel")

        self.Add(more_item, 0, wx.EXPAND)

    def remove_more_panel(self):
        if self.more:
            more_panel: LoadMoreTaskItemPanel = wx.FindWindowByName("more_panel", self)

            if more_panel:
                more_panel.destroy_panel()

            self.more = False

    def Remove(self):
        if self.sizer.IsEmpty():
            self.add_empty_panel()

    def get_items_count(self):
        return self.sizer.GetItemCount() - int(self.empty) - int(self.more)