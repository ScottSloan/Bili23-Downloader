import wx
from typing import Callable

from gui.component.panel.scrolled_panel import ScrolledPanel
from gui.component.panel.panel import Panel

class EmptyItemPanel(Panel):
    def __init__(self, parent, label: str):
        self.label = label

        Panel.__init__(self, parent)

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
    def __init__(self, parent, left_count: int, load_more_callback: Callable):
        self.count, self.callback = left_count, load_more_callback

        Panel.__init__(self, parent)

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
        self.destroy_panel()

        self.callback()

    def destroy_panel(self):
        self.Hide()
        self.Destroy()

class ScrolledPanelList(ScrolledPanel):
    def __init__(self, parent, info: dict):
        self.info = info

        ScrolledPanel.__init__(self, parent)

        self.init_utils()

    def init_utils(self):
        self.add_empty_panel()

    def Show(self):
        pass

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

        empty_item = EmptyItemPanel(self, self.info.get("empty_label"))

        self.Add(empty_item, 1, wx.EXPAND)

    def remove_empty_panel(self):
        if self.empty and not self.sizer.IsEmpty():
            empty_panel: EmptyItemPanel = self.sizer.GetItem(0).GetWindow()

            empty_panel.destroy_panel()

            self.empty = False

    def Remove(self):
        if self.sizer.IsEmpty():
            self.add_empty_panel()
