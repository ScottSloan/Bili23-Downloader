import wx
import gettext

from utils.common.style.icon_v4 import Icon, IconID, IconSize

from utils.parse.episode.episode_v2 import Episode

from gui.component.window.frame import Frame
from gui.component.panel.panel import Panel

from gui.component.button.bitmap_button import BitmapButton
from gui.component.text_ctrl.search_ctrl import SearchCtrl

_ = gettext.gettext

class Flag:
    loop = False

class SearchResult:
    def __init__(self, data: list):
        self.data = data
        self.length = len(data)
        self.index = -1

    def next(self):
        if Flag.loop and self.index + 1 > self.length - 1:
            self.index = 0
        else:
            self.index = min(self.index + 1, self.length - 1)

        return self.data[self.index]
    
    def prev(self):
        if Flag.loop and self.index - 1 < 0:
            self.index = self.length - 1
        else:
            self.index = max(0, self.index - 1)

        return self.data[self.index]

class SearchEpisodeListDialog(Frame):
    def __init__(self, parent: wx.Window):
        from gui.window.main.main_v3 import MainWindow

        self.parent: MainWindow = parent

        Frame.__init__(self, parent, _("搜索"), style = wx.DEFAULT_FRAME_STYLE & (~wx.RESIZE_BORDER) | wx.FRAME_TOOL_WINDOW | wx.FRAME_FLOAT_ON_PARENT, name = "search")

        self.init_UI()

        self.Bind_EVT()

        self.CenterOnParent()

        self.search_result = SearchResult([])

    def init_UI(self):
        panel = Panel(self)

        self.search_box = SearchCtrl(panel, _("在剧集列表中搜索"), size = self.FromDIP((300, -1)), search_btn = True, clear_btn = True)
        self.search_box.SetValue(self.parent.search_keywords)

        self.search_result_lab = wx.StaticText(panel, -1, _("无结果"))
        self.previous_btn = BitmapButton(panel, Icon.get_icon_bitmap(IconID.Up, icon_size = IconSize.SMALL_EX))
        self.previous_btn.SetToolTip(_("上一匹配项"))
        self.previous_btn.Enable(False)
        self.next_btn = BitmapButton(panel, Icon.get_icon_bitmap(IconID.Down, icon_size = IconSize.SMALL_EX))
        self.next_btn.SetToolTip(_("下一匹配项"))
        self.next_btn.Enable(False)
        self.search_btn = wx.Button(panel, wx.ID_OK, _("搜索"), size = self.get_scaled_size((80, 30)))

        search_hbox = wx.BoxSizer(wx.HORIZONTAL)

        search_hbox.Add(self.search_result_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
        search_hbox.Add(self.previous_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        search_hbox.Add(self.next_btn, 0, wx.ALL & (~wx.LEFT) & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
        search_hbox.AddStretchSpacer()
        search_hbox.Add(self.search_btn, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))

        self.show_matches_only_chk = wx.CheckBox(panel, -1, _("仅显示匹配项"))
        self.loop_search_chk = wx.CheckBox(panel, -1, _("循环搜索"))
        self.check_all_chk = wx.CheckBox(panel, -1, _("全选"))

        option_hbox = wx.BoxSizer(wx.HORIZONTAL)
        option_hbox.Add(self.show_matches_only_chk, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
        option_hbox.Add(self.loop_search_chk, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
        option_hbox.Add(self.check_all_chk, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.search_box, 0, wx.ALL | wx.EXPAND, self.FromDIP(6))
        vbox.Add(search_hbox, 0, wx.EXPAND)
        vbox.Add(option_hbox, 0, wx.EXPAND)

        panel.SetSizer(vbox)

        dlg_vbox = wx.BoxSizer(wx.VERTICAL)
        dlg_vbox.Add(panel, 0, wx.EXPAND)

        self.SetSizerAndFit(dlg_vbox)        

    def Bind_EVT(self):
        self.Bind(wx.EVT_CLOSE, self.onCloseEVT)

        self.search_btn.Bind(wx.EVT_BUTTON, self.onSearchEVT)
        self.search_box.Bind(wx.EVT_SEARCH, self.onSearchEVT)

        self.previous_btn.Bind(wx.EVT_BUTTON, self.onPreviousItemEVT)
        self.next_btn.Bind(wx.EVT_BUTTON, self.onNextItemEVT)

        self.show_matches_only_chk.Bind(wx.EVT_CHECKBOX, self.onShowMatchesOnlyEVT)
        self.loop_search_chk.Bind(wx.EVT_CHECKBOX, self.onLoopEVT)
        self.check_all_chk.Bind(wx.EVT_CHECKBOX, self.onCheckAllEVT)

    def onCloseEVT(self, event: wx.CloseEvent):
        self.parent.search_keywords = self.search_box.GetValue()
        
        event.Skip()

    def onSearchEVT(self, event: wx.CommandEvent):
        keywords = self.search_box.GetValue()

        self.update_episode_list(keywords)

        if keywords:
            result = self.parent.episode_list.SearchItem(keywords)
        else:
            result = []
        
        self.search_result = SearchResult(result)

        if result:
            self.onNextItemEVT(0)

        self.update_index()

        self.onCheckAllEVT(event)

    def onPreviousItemEVT(self, event: wx.CommandEvent):
        item = self.search_result.prev()

        self.parent.episode_list.FocusItem(item)

        self.update_index()

    def onNextItemEVT(self, event: wx.CommandEvent):
        item = self.search_result.next()

        self.parent.episode_list.FocusItem(item)

        self.update_index()

    def onShowMatchesOnlyEVT(self, event: wx.CommandEvent):
        if self.search_result.length:
            self.onSearchEVT(event)

    def onLoopEVT(self, event: wx.CommandEvent):
        Flag.loop = self.loop_search_chk.GetValue()

    def onCheckAllEVT(self, event: wx.CommandEvent):
        if data := self.search_result.data.copy():
            if self.check_all_chk.GetValue():
                self.parent.episode_list.CheckItems(data)
            else:
                self.parent.episode_list.UnCheckItems(data)

    def update_index(self):
        len = self.search_result.length

        self.previous_btn.Enable(len)
        self.next_btn.Enable(len)

        self.search_result_lab.SetLabel(_("第 %s 项，共 %s 项") % (self.search_result.index + 1, len) if len else _("无结果"))

        self.Layout()

    def update_episode_list(self, keywords: str):
        Episode.Utils.search_episode(keywords, show_matches_only = self.show_matches_only_chk.GetValue())

        if keywords:
            self.parent.show_episode_list(from_menu = False)

    def reset(self):
        self.search_result = SearchResult([])

        self.update_index()