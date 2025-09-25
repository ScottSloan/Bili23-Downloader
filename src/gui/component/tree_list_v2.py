import wx.dataview

from utils.config import Config

from utils.common.enums import Platform
from utils.common.model.list_item_info import TreeListItemInfo
from utils.common.formatter.formatter import FormatUtils
from utils.common.model.download_info import DownloadInfo

from utils.parse.episode.episode_v2 import EpisodeInfo, Episode

from gui.component.menu.episode_list import EpisodeListMenu

class TreeListCtrl(wx.dataview.TreeListCtrl):
    def __init__(self, parent: wx.Window):
        from gui.window.main.main_v3 import MainWindow

        self.main_window: MainWindow = wx.FindWindowByName("main")

        wx.dataview.TreeListCtrl.__init__(self, parent, -1, style = wx.dataview.TL_3STATE)

        self.init_list_params()

        self.Bind_EVT()

        self.init_episode_list()

    def Bind_EVT(self):
        self.Bind(wx.dataview.EVT_TREELIST_ITEM_CHECKED, self.onItemCheckedEVT)
        self.Bind(wx.dataview.EVT_TREELIST_ITEM_ACTIVATED, self.onItemActivatedEVT)
        self.Bind(wx.dataview.EVT_TREELIST_ITEM_CONTEXT_MENU, self.onItemContextMenuEVT)

        self.Bind(wx.EVT_SIZE, self.onSizeEVT)

    def init_episode_list(self):
        self.ClearColumns()
        self.DeleteAllItems()

        self.AppendColumn("序号", width = self.FromDIP(100 if Platform(Config.Sys.platform) != Platform.Linux else 125))
        self.AppendColumn("标题", width = self.FromDIP(385))
        self.AppendColumn("备注", width = self.FromDIP(75))
        self.AppendColumn("时长", width = self.FromDIP(75))

        self.shift_down_items: list[int] = []

    def show_episode_list(self):
        def add_item(data: dict | list, item: wx.dataview.TreeListItem):
            if isinstance(data, dict):
                item = self.AppendItem(item, "")

                set_item(data, item)

                if (entries := data.get("entries")):
                    for value in entries:
                        add_item(value, item)

            elif isinstance(data, list):
                for entry in data:
                    add_item(entry, item)

        def set_item(data: dict, item: wx.dataview.TreeListItem):
            if "entries" in data:

                self.SetItemText(item, 0, data["label"])
                self.SetItemText(item, 1, data["title"])

                if "duration" in data and data["duration"]:
                    self.SetItemText(item, 3, FormatUtils.format_episode_duration(data["duration"]))

            else:
                self.count += 1

                self.SetItemText(item, 0, str(self.count))
                self.SetItemText(item, 1, data["title"])
                self.SetItemText(item, 2, data["badge"])
                self.SetItemText(item, 3, FormatUtils.format_episode_duration(data["duration"]))

            item_data = TreeListItemInfo()
            item_data.load_from_dict(data)

            item_data.number = self.count

            self.SetItemData(item, item_data)

            self.Expand(item)

        self.init_episode_list()

        self.count = 0

        add_item(EpisodeInfo.filted_data.copy(), self.GetRootItem())

    def onItemActivatedEVT(self, event):
        item = self.GetSelection()

        data: TreeListItemInfo = self.GetItemData(item)
        print(data.to_dict())

    def onItemCheckedEVT(self, event: wx.dataview.TreeListEvent):
        item = event.GetItem()

        self.UpdateItemParentStateRecursively(item)

        if wx.GetKeyState(wx.WXK_SHIFT):
            current = self.GetItemData(item).number

            self.shift_down_items.append(current)

            first = self.shift_down_items[0]
            last = self.shift_down_items[-1]

            self.CheckItemRange(min(first, last), max(first, last))
            
        if self.GetFirstChild(item).IsOk():
            self.CheckItemRecursively(item, state = wx.CHK_UNCHECKED if event.GetOldCheckedState() else wx.CHK_CHECKED)

        self.main_window.top_box.update_checked_item_count(self.GetCheckedItemCount())

    def onItemContextMenuEVT(self, event):
        if self.GetSelection().IsOk():
            menu = EpisodeListMenu(self.GetCurrentItemType(), self.GetCurrentItemCheckedState(), self.GetCurrentItemCollapsedState())

            self.PopupMenu(menu)

    def onSizeEVT(self, event):
        width, height = self.GetSize()

        self.SetColumnWidth(1, width - self.FromDIP(350))

        event.Skip()

    def CheckCurrentItem(self):
        item = self.GetSelection()

        match self.GetCheckedState(item):
            case wx.CHK_CHECKED | wx.CHK_UNDETERMINED:
                state = wx.CHK_UNCHECKED
            
            case wx.CHK_UNCHECKED:
                state = wx.CHK_CHECKED

        self.CheckItemRecursively(item, state)

        self.UpdateItemParentStateRecursively(item)

        self.main_window.top_box.update_checked_item_count(self.GetCheckedItemCount())

    def CheckItemRange(self, start_number: int, end_number: int, uncheck_all: bool = True):
        if uncheck_all:
            self.UnCheckAllItems()

        item = wx.dataview.TreeListItem = self.GetFirstChild(self.GetRootItem())
        start_flag = False

        while item.IsOk():
            if (item_data := self.GetItemData(item)) and item_data.item_type == "item":
                if item_data.number == start_number:
                    start_flag = True

                if start_flag:
                    self.CheckItemRecursively(item, wx.CHK_CHECKED)
                    self.UpdateItemParentStateRecursively(item)

                if item_data.number == end_number:
                    break

            item = self.GetNextItem(item)

        self.main_window.top_box.update_checked_item_count(self.GetCheckedItemCount())

    def CollapseCurrentItem(self):
        item = self.GetSelection()

        if self.IsExpanded(item):
            self.Collapse(item)
        else:
            self.Expand(item)

    def CheckAllItems(self):
        self.CheckItemRecursively(self.GetFirstItem(), wx.CHK_CHECKED)

    def UnCheckAllItems(self):
        self.CheckItemRecursively(self.GetFirstItem(), wx.CHK_UNCHECKED)

    def GetAllCheckedItem(self):
        self.download_task_info_list = []

        item: wx.dataview.TreeListItem = self.GetFirstChild(self.GetRootItem())

        while item.IsOk():
            if self.GetItemData(item).item_type == "item" and self.GetCheckedState(item) == wx.CHK_CHECKED:
                item_data = self.GetItemData(item)

                self.download_task_info_list.extend(DownloadInfo.get_download_info(item_data))

            item = self.GetNextItem(item)
    
    def SearchItem(self, keywords: str):
        result = []

        item: wx.dataview.TreeListItem = self.GetFirstChild(self.GetRootItem())

        while item.IsOk():
            item_data = self.GetItemData(item)

            if keywords in item_data.title:
                result.append(item)

            item = self.GetNextItem(item)

        return result
    
    def FocusItem(self, item):
        self.EnsureVisible(item)
        self.Select(item)

    def GetCurrentItemType(self):
        item = self.GetSelection()

        return self.GetItemData(item).item_type
    
    def GetCurrentItemCheckedState(self):
        item = self.GetSelection()

        match self.GetCheckedState(item):
            case wx.CHK_CHECKED | wx.CHK_UNDETERMINED:
                return True
            
            case wx.CHK_UNCHECKED:
                return False

    def GetCurrentItemCollapsedState(self):
        item = self.GetSelection()

        return not self.IsExpanded(item)

    def GetCheckedItemCount(self):
        count = 0

        item: wx.dataview.TreeListItem = self.GetFirstChild(self.GetRootItem())

        while item.IsOk():
            if self.GetItemData(item).item_type == "item" and self.GetCheckedState(item) == wx.CHK_CHECKED:
                count += 1

            item = self.GetNextItem(item)

        if not count:
            self.shift_down_items.clear()

        return count
    
    def GetItemData(self, item) -> TreeListItemInfo:
        return super().GetItemData(item)

    def SetItemTitle(self, item: wx.dataview.TreeListItem, title: str):
        item_data = self.GetItemData(item)

        item_data.title = title

        self.SetItemText(item, 1, title)
        self.SetItemData(item, item_data)

    def GetItemTitle(self):
        return self.GetItemText(self.GetSelection(), 1)
    
    def GetCurrentEpisodeInfo(self):
        return Episode.Utils.get_first_episode()
    
    def CheckItems(self, items: list):
        for item in items:
            self.CheckItemRecursively(item, wx.CHK_CHECKED)
            self.UpdateItemParentStateRecursively(item)

    def UnCheckItems(self, items: list):
        for item in items:
            self.CheckItemRecursively(item, wx.CHK_UNCHECKED)
            self.UpdateItemParentStateRecursively(item)

    def GetFirstCheckedItem(self):
        item = self.GetFirstChild(self.GetRootItem())

        while item.IsOk():
            if (item_data := self.GetItemData(item)) and item_data.item_type == "item" and self.GetCheckedState(item) == wx.CHK_CHECKED:
                return item
            
            item = self.GetNextItem(item)

        return None

    def check_download_items(self):
        if not self.main_window.episode_list.GetCheckedItemCount():
            from gui.window.main.main_v3 import Window

            Window.message_dialog(self.main_window, "下载失败\n\n请选择要下载的项目。", "警告", wx.ICON_WARNING)
            
            return True
        
    def init_list_params(self):
        match Platform(Config.Sys.platform):
            case Platform.Windows:
                self.SetSize(self.FromDIP((775, 300)))
            
            case Platform.Linux | Platform.macOS:
                self.SetSize(self.FromDIP((775, 350)))