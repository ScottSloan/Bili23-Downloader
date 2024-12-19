import io
import wx
import wx.dataview
from typing import Optional
from wx.lib.scrolledpanel import ScrolledPanel as _ScrolledPanel

from utils.icon_v2 import IconManager, APP_ICON_SMALL
from utils.tool_v2 import UniversalTool
from utils.config import Config
from utils.parse.video import VideoInfo
from utils.parse.bangumi import BangumiInfo
from utils.parse.live import LiveInfo
from utils.parse.audio import AudioInfo
from utils.parse.extra import ExtraInfo
from utils.parse.episode import EpisodeInfo
from utils.data_type import DownloadTaskInfo, TreeListItemInfo

class Frame(wx.Frame):
    def __init__(self, parent, title, style = wx.DEFAULT_FRAME_STYLE):
        wx.Frame.__init__(self, parent, -1, title, style = style)

        icon_manager = IconManager(self.GetDPIScaleFactor())

        self.SetIcon(wx.Icon(wx.Image(io.BytesIO(icon_manager.get_icon_bytes(APP_ICON_SMALL))).ConvertToBitmap()))

        self.panel = wx.Panel(self)

class TreeListCtrl(wx.dataview.TreeListCtrl):
    def __init__(self, parent):
        wx.dataview.TreeListCtrl.__init__(self, parent, -1, style = wx.dataview.TL_3STATE)

        self.Bind_EVT()

        self.init_list()

        self._main_window = self.GetParent().GetParent()
    
    def Bind_EVT(self):
        self.Bind(wx.dataview.EVT_TREELIST_ITEM_CHECKED, self.onCheckItem)

    def init_list(self):
        self.ClearColumns()
        self.DeleteAllItems()
        
        self.AppendColumn("序号", width = self.FromDIP(85))
        self.AppendColumn("标题", width = self.FromDIP(375))
        self.AppendColumn("备注", width = self.FromDIP(50))
        self.AppendColumn("时长", width = self.FromDIP(75))

    def set_list(self):
        def _gen(data: list | dict, node):
            def set_item(data: dict):
                if "entries" in data:
                    self.SetItemText(item, 0, str(data["title"]))

                    if "duration" in data and data["duration"]:
                        self.SetItemText(item, 3, data["duration"])

                    self.SetItemData(item, _get_item_data("node", data["title"]))
                else:
                    self._index += 1

                    self.SetItemText(item, 0, str(self._index))
                    self.SetItemText(item, 1, data["title"])
                    self.SetItemText(item, 2, data["badge"])
                    self.SetItemText(item, 3, data["duration"])
                    
                    self.SetItemData(item, _get_item_data("item", data["title"], data["cid"]))

                if Config.Misc.auto_select:
                    self.CheckItem(item, wx.CHK_CHECKED)

                self.Expand(node)

            if isinstance(data, list):
                for entry in data:
                    _gen(entry, node)

            elif isinstance(data, dict):
                item = self.AppendItem(node, "")
                
                set_item(data)

                for value in data.values():
                    _gen(value, item)

        def _get_item_data(type: str, title: str, cid: int = 0):
            data = TreeListItemInfo()
            data.type = type
            data.title = title
            data.cid = cid

            return data

        self._index = 0

        _gen(EpisodeInfo.data, self.GetRootItem())

    def set_live_list(self):
        live_list = {}
        
        live_list["直播"] = [["1", LiveInfo.title, LiveInfo.status_str, "--:--:--"]]
        self.parent_items.append("直播")

        self.set_list(live_list)

    def onCheckItem(self, event):
        item = event.GetItem()

        self.UpdateItemParentStateRecursively(item)

        if self.GetFirstChild(item).IsOk():
            self.CheckItemRecursively(item, state = wx.CHK_UNCHECKED if event.GetOldCheckedState() else wx.CHK_CHECKED)
    
    def get_all_selected_item(self, video_quality_id: Optional[int] = None):
        def get_item_info(title: str, cid: int):
            match self._main_window.current_parse_type:
                case Config.Type.VIDEO:
                    self.get_video_download_info(title, EpisodeInfo.cid_dict.get(cid))

                case Config.Type.BANGUMI:
                    self.get_bangumi_download_info(title, EpisodeInfo.cid_dict.get(cid))

        self.video_quality_id = video_quality_id
        self.download_task_info_list = []

        item: wx.dataview.TreeListItem = self.GetFirstChild(self.GetRootItem())

        while item.IsOk():
            item = self.GetNextItem(item)

            if item.IsOk():
                if self.GetItemData(item).type == "item" and self.GetCheckedState(item) == wx.CHK_CHECKED:
                    title = self.GetItemData(item).title
                    cid = self.GetItemData(item).cid
                    
                    if cid:
                        get_item_info(title, cid)
    
    def format_info_entry(self, referer_url: str, download_type: int, title: str, duration: int, cover_url: Optional[str] = None, bvid: Optional[str] = None, cid: Optional[int] = None):
        download_info = DownloadTaskInfo()

        download_info.id = UniversalTool.get_random_id()
        download_info.timestamp = UniversalTool.get_timestamp(us = True)

        download_info.title = title
        download_info.title_legal = UniversalTool.get_legal_name(title)
        download_info.cover_url = cover_url
        download_info.referer_url = referer_url
        download_info.bvid = bvid
        download_info.cid = cid
        download_info.duration = duration

        download_info.video_quality_id = self.video_quality_id
        download_info.audio_quality_id = AudioInfo.audio_quality_id

        if AudioInfo.download_audio_only:
            download_info.video_merge_type = Config.Type.MERGE_TYPE_AUDIO

        download_info.download_type = download_type

        download_info.get_danmaku = ExtraInfo.get_danmaku
        download_info.danmaku_type = ExtraInfo.danmaku_type
        download_info.get_cover = ExtraInfo.get_cover

        return download_info

    def get_video_download_info(self, title: str, entry: dict):
        if "arc" in entry:
            cover_url = entry["arc"]["pic"]
            duration = entry["arc"]["duration"]
            bvid = entry["bvid"]
        else:
            cover_url = VideoInfo.cover
            bvid = VideoInfo.bvid
            duration = entry["duration"]

        cid = entry["cid"]
        referer_url = VideoInfo.url

        self.download_task_info_list.append(self.format_info_entry(referer_url, Config.Type.VIDEO, title, duration, cover_url, bvid, cid))
    
    def get_bangumi_download_info(self, title: str, entry: dict):
        cover_url = entry["cover"]
        bvid = entry["bvid"]
        cid = entry["cid"]

        if "duration" in entry:
            duration = entry["duration"] / 1000
        else:
            duration = 0

        referer_url = BangumiInfo.url

        self.download_task_info_list.append(self.format_info_entry(referer_url, Config.Type.BANGUMI, title, duration, cover_url, bvid, cid))

class ScrolledPanel(_ScrolledPanel):
    def __init__(self, parent, size):
        _ScrolledPanel.__init__(self, parent, -1, size = size)

        self.sizer = wx.BoxSizer(wx.VERTICAL)

        self.SetSizer(self.sizer)

class InfoBar(wx.InfoBar):
    def __init__(self, parent):
        wx.InfoBar.__init__(self, parent, -1)

    def ShowMessage(self, msg, flags=...):
        super().Dismiss()
        return super().ShowMessage(msg, flags)
