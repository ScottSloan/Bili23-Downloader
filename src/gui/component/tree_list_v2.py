import wx.dataview

from utils.config import Config

from utils.common.enums import Platform, ParseType
from utils.common.data_type import TreeListItemInfo, TreeListCallback
from utils.common.formatter import FormatUtils
from utils.common.download_info import DownloadInfo

from utils.parse.episode_v2 import EpisodeInfo

class TreeListCtrl(wx.dataview.TreeListCtrl):
    def __init__(self, parent, callback: TreeListCallback):
        def get_size():
            match Platform(Config.Sys.platform):
                case Platform.Windows:
                    return self.FromDIP((775, 300))
                
                case Platform.Linux | Platform.macOS:
                    return self.FromDIP((775, 350))
        
        self.callback = callback

        wx.dataview.TreeListCtrl.__init__(self, parent, -1, style = wx.dataview.TL_3STATE)

        self.SetSize(get_size())

        self.Bind_EVT()

        self.init_id()

        self.init_episode_list()

    def Bind_EVT(self):
        self.Bind(wx.dataview.EVT_TREELIST_ITEM_CHECKED, self.onItemCheckedEVT)
        self.Bind(wx.dataview.EVT_TREELIST_ITEM_ACTIVATED, self.onItemActivatedEVT)
        self.Bind(wx.dataview.EVT_TREELIST_ITEM_CONTEXT_MENU, self.onItemContextMenuEVT)

        self.Bind(wx.EVT_SIZE, self.onSizeEVT)

    def init_id(self):
        self.ID_EPISODE_LIST_VIEW_COVER_MENU = wx.NewIdRef()
        self.ID_EPISODE_LIST_COPY_TITLE_MENU = wx.NewIdRef()
        self.ID_EPISODE_LIST_COPY_URL_MENU = wx.NewIdRef()
        self.ID_EPISODE_LIST_EDIT_TITLE_MENU = wx.NewIdRef()
        self.ID_EPISODE_LIST_CHECK_MENU = wx.NewIdRef()
        self.ID_EPISODE_LIST_COLLAPSE_MENU = wx.NewIdRef()

    def init_episode_list(self):
        self.ClearColumns()
        self.DeleteAllItems()

        self.AppendColumn("序号", width = self.FromDIP(100))
        self.AppendColumn("标题", width = self.FromDIP(385))
        self.AppendColumn("备注", width = self.FromDIP(75))
        self.AppendColumn("时长", width = self.FromDIP(75))

        dv = self.GetDataView()

        dv.SetIndent(20)

    def show_episode_list(self):
        def add_item(data: dict | list, item: wx.dataview.TreeListItem):
            if isinstance(data, dict):
                item = self.AppendItem(item, "")

                set_item(data, item)

                for value in data.values():
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

        add_item(EpisodeInfo.data, self.GetRootItem())

    def onItemActivatedEVT(self, event):
        item = self.GetSelection()

        data: TreeListItemInfo = self.GetItemData(item)
        print(data.to_dict())

    def onItemCheckedEVT(self, event: wx.dataview.TreeListEvent):
        item = event.GetItem()

        self.UpdateItemParentStateRecursively(item)

        if self.GetFirstChild(item).IsOk():
            self.CheckItemRecursively(item, state = wx.CHK_UNCHECKED if event.GetOldCheckedState() else wx.CHK_CHECKED)

        self.callback.onUpdateCheckedItemCount(self.GetCheckedItemCount())

    def onItemContextMenuEVT(self, event):
        menu = wx.Menu()

        view_cover_menuitem = wx.MenuItem(menu, self.ID_EPISODE_LIST_VIEW_COVER_MENU, "查看封面(&V)")
        copy_title_menuitem = wx.MenuItem(menu, self.ID_EPISODE_LIST_COPY_TITLE_MENU, "复制标题(&C)")
        copy_url_menuitem = wx.MenuItem(menu, self.ID_EPISODE_LIST_COPY_URL_MENU, "复制链接(&U)")
        edit_title_menuitem = wx.MenuItem(menu, self.ID_EPISODE_LIST_EDIT_TITLE_MENU, "修改标题(&E)")
        check_menuitem = wx.MenuItem(menu, self.ID_EPISODE_LIST_CHECK_MENU, "取消选择(&N)" if self.GetCurrentItemCheckedState() else "选择(&S)")
        collapse_menuitem = wx.MenuItem(menu, self.ID_EPISODE_LIST_COLLAPSE_MENU, "展开(&X)" if self.GetCurrentItemCollapsedState() else "折叠(&O)")

        if self.GetCurrentItemType() == "node":
            view_cover_menuitem.Enable(False)
            copy_title_menuitem.Enable(False)
            copy_url_menuitem.Enable(False)
            edit_title_menuitem.Enable(False)
        else:
            collapse_menuitem.Enable(False)

        menu.Append(view_cover_menuitem)
        menu.AppendSeparator()
        menu.Append(copy_title_menuitem)
        menu.Append(copy_url_menuitem)
        menu.AppendSeparator()
        menu.Append(edit_title_menuitem)
        menu.AppendSeparator()
        menu.Append(check_menuitem)
        menu.Append(collapse_menuitem)

        if self.GetSelection().IsOk():
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

    def CollapseCurrentItem(self):
        item = self.GetSelection()

        if self.IsExpanded(item):
            self.Collapse(item)
        else:
            self.Expand(item)

    def CheckAllItems(self):
        self.CheckItemRecursively(self.GetRootItem(), wx.CHK_CHECKED)

    def GetAllCheckedItem(self, parse_type: ParseType, video_quality_id: int):
        self.download_task_info_list = []

        item: wx.dataview.TreeListItem = self.GetFirstChild(self.GetRootItem())

        while item.IsOk():
            item = self.GetNextItem(item)

            if item.IsOk():
                if self.GetItemData(item).item_type == "item" and self.GetCheckedState(item) == wx.CHK_CHECKED:
                    item_data = self.GetItemData(item)

                    if item_data.cid:
                        self.download_task_info_list.extend(DownloadInfo.get_download_info(item_data, parse_type, video_quality_id))

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
            item = self.GetNextItem(item)

            if item.IsOk():
                if self.GetItemData(item).item_type == "item" and self.GetCheckedState(item) == wx.CHK_CHECKED:
                    count += 1

        return count

    def GetItemData(self, item) -> TreeListItemInfo:
        return super().GetItemData(item)

    def SetItemTitle(self, item: wx.dataview.TreeListItem, title: str):
        item_data = self.GetItemData(item)

        item_data.title = title

        self.SetItemText(item, 1, title)
        self.SetItemData(item, item_data)