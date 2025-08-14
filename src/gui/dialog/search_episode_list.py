import wx

from utils.common.style.icon_v4 import Icon, IconID

from gui.component.window.frame import Frame
from gui.component.panel.panel import Panel

from gui.component.button.bitmap_button import BitmapButton
from gui.component.text_ctrl.search_ctrl import SearchCtrl

class SearchResult:
    def __init__(self, data: list):
        self.data = data
        self.length = len(data)
        self.index = -1

    def next(self):
        self.index = min(self.index + 1, self.length - 1)
        return self.data[self.index]
    
    def prev(self):
        self.index = max(0, self.index - 1)
        return self.data[self.index]

class SearchEpisodeListDialog(Frame):
    def __init__(self, parent: wx.Window):
        from gui.window.main.main_v3 import MainWindow

        self.parent: MainWindow = parent

        Frame.__init__(self, parent, "搜索", style = wx.DEFAULT_FRAME_STYLE | wx.FRAME_TOOL_WINDOW | wx.FRAME_FLOAT_ON_PARENT, name = "search")

        self.init_UI()

        self.Bind_EVT()

        self.CenterOnParent()

    def init_UI(self):
        panel = Panel(self)

        self.search_box = SearchCtrl(panel, "在剧集列表中搜索", size = self.FromDIP((300, 24)), search_btn = True, clear_btn = True)

        self.search_result_lab = wx.StaticText(panel, -1, "无结果")
        self.previous_btn = BitmapButton(panel, Icon.get_icon_bitmap(IconID.Up))
        self.previous_btn.SetToolTip("上一匹配项")
        self.previous_btn.Enable(False)
        self.next_btn = BitmapButton(panel, Icon.get_icon_bitmap(IconID.Down))
        self.next_btn.SetToolTip("下一匹配项")
        self.next_btn.Enable(False)
        self.search_btn = wx.Button(panel, wx.ID_OK, "搜索", size = self.get_scaled_size((80, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)

        bottom_hbox.Add(self.search_result_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
        bottom_hbox.Add(self.previous_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        bottom_hbox.Add(self.next_btn, 0, wx.ALL & (~wx.LEFT) & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(self.search_btn, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.search_box, 0, wx.ALL | wx.EXPAND, self.FromDIP(6))
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        panel.SetSizer(vbox)

        dlg_vbox = wx.BoxSizer(wx.VERTICAL)
        dlg_vbox.Add(panel, 0, wx.EXPAND)

        self.SetSizerAndFit(dlg_vbox)

    def Bind_EVT(self):
        self.search_btn.Bind(wx.EVT_BUTTON, self.onSearchEVT)
        self.search_box.Bind(wx.EVT_SEARCH, self.onSearchEVT)

        self.previous_btn.Bind(wx.EVT_BUTTON, self.onPreviousItemEVT)
        self.next_btn.Bind(wx.EVT_BUTTON, self.onNextItemEVT)
        
    def onSearchEVT(self, event: wx.CommandEvent):
        keywords = self.search_box.GetValue()

        if keywords:
            result = self.parent.episode_list.SearchItem(keywords)
        else:
            result = []
        
        self.search_result = SearchResult(result)

        if result:
            self.onNextItemEVT(0)

        self.update_index()

    def onPreviousItemEVT(self, event: wx.CommandEvent):
        item = self.search_result.prev()

        self.parent.episode_list.FocusItem(item)

        self.update_index()

    def onNextItemEVT(self, event: wx.CommandEvent):
        item = self.search_result.next()

        self.parent.episode_list.FocusItem(item)

        self.update_index()

    def update_index(self):
        len = self.search_result.length

        self.previous_btn.Enable(len)
        self.next_btn.Enable(len)

        self.search_result_lab.SetLabel(f"第 {self.search_result.index + 1} 项，共 {len} 项" if len else "无结果")

        self.Layout()