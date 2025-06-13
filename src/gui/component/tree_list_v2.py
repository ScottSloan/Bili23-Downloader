import json
import wx.dataview

from utils.config import Config

from utils.common.enums import Platform
from utils.common.data_type import TreeListItemInfo
from utils.common.formatter import FormatUtils

from utils.parse.episode_v2 import EpisodeInfo

class TreeListCtrl(wx.dataview.TreeListCtrl):
    def __init__(self, parent, callback):
        def get_size():
            match Platform(Config.Sys.platform):
                case Platform.Windows:
                    return self.FromDIP((775, 300))
                
                case Platform.Linux | Platform.macOS:
                    return self.FromDIP((775, 350))
                
        wx.dataview.TreeListCtrl.__init__(self, parent, -1, style = wx.dataview.TL_3STATE)

        self.SetSize(get_size())

        self.Bind_EVT()

        self.init_episode_list()

    def Bind_EVT(self):
        self.Bind(wx.dataview.EVT_TREELIST_ITEM_ACTIVATED, self.onItemActivatedEVT)

    def init_episode_list(self):
        self.ClearColumns()
        self.DeleteAllItems()

        self.AppendColumn("序号", width = self.FromDIP(100))
        self.AppendColumn("标题", width = self.FromDIP(385))
        self.AppendColumn("备注", width = self.FromDIP(75))
        self.AppendColumn("时长", width = self.FromDIP(75))

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

            self.SetItemData(item, item_data)

            self.Expand(item)

        self.init_episode_list()

        self.count = 0

        add_item(EpisodeInfo.data, self.GetRootItem())

        dv = self.GetDataView()

        dv.SetIndent(20)

        #renderer = wx.dataview.DataViewTextRenderer()
        #renderer.EnableMarkup()
        #self.GetDataView().AppendColumn(wx.dataview.DataViewColumn("title", renderer, 0))

        # dv.SetWindowStyleFlag(wx.dataview.DV_VERT_RULES)

        # with open("episode.json", "w", encoding = "utf-8") as f:
        #     f.write(json.dumps(EpisodeInfo.data, ensure_ascii = False))

    def onItemActivatedEVT(self, event):
        item = self.GetSelection()

        data: TreeListItemInfo = self.GetItemData(item)
        print(data.to_dict())