import wx
import random
import time
import wx.dataview
from typing import Optional
from wx.lib.scrolledpanel import ScrolledPanel as _ScrolledPanel

from utils.config import Config
from utils.common.icon_v2 import IconManager, IconType
from utils.common.data_type import DownloadTaskInfo, TreeListItemInfo
from utils.common.enums import ParseType, DownloadOption

from utils.parse.video import VideoInfo
from utils.parse.bangumi import BangumiInfo
from utils.parse.audio import AudioInfo
from utils.parse.extra import ExtraInfo
from utils.parse.episode import EpisodeInfo
from utils.parse.cheese import CheeseInfo

class Frame(wx.Frame):
    def __init__(self, parent, title, style = wx.DEFAULT_FRAME_STYLE):
        wx.Frame.__init__(self, parent, -1, title, style = style)

        icon_manager = IconManager(self)

        self.SetIcon(wx.Icon(icon_manager.get_icon_bitmap(IconType.APP_ICON_SMALL)))

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
        self.AppendColumn("备注", width = self.FromDIP(75))
        self.AppendColumn("时长", width = self.FromDIP(75))

    def set_list(self):
        def _gen(data: list | dict, node):
            def set_item(data: dict):
                if "entries" in data:
                    self.SetItemText(item, 0, str(data["title"]))

                    if "collection_title" in data and data["collection_title"]:
                        self.SetItemText(item, 1, data["collection_title"])

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

                    _column_width = self.WidthFor(data["title"])

                    if _column_width > self._title_longest_width:
                        self._title_longest_width = _column_width

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

        self._index, self._title_longest_width = 0, 0

        _gen(EpisodeInfo.data, self.GetRootItem())

        if self._title_longest_width > self.FromDIP(375):
            self.SetColumnWidth(1, self._title_longest_width + 15)

    def is_current_item_checked(self):
        match self.GetCheckedState(self.GetSelection()):
            case wx.CHK_CHECKED | wx.CHK_UNDETERMINED:
                return True
            
            case wx.CHK_UNCHECKED:
                return False

    def is_current_item_collapsed(self):
        item = self.GetSelection()

        return not self.IsExpanded(item)
    
    def is_current_item_node(self):
        item = self.GetSelection()

        return self.GetItemData(item).type == "node"

    def check_current_item(self):
        item = self.GetSelection()

        match self.GetCheckedState(item):
            case wx.CHK_CHECKED | wx.CHK_UNDETERMINED:
                state = wx.CHK_UNCHECKED
            
            case wx.CHK_UNCHECKED:
                state = wx.CHK_CHECKED

        self.CheckItemRecursively(item, state)

        self.UpdateItemParentStateRecursively(item)
    
    def collapse_current_item(self):
        item = self.GetSelection()

        if self.IsExpanded(item):
            self.Collapse(item)
        else:
            self.Expand(item)

    def onCheckItem(self, event):
        item = event.GetItem()

        self.UpdateItemParentStateRecursively(item)

        if self.GetFirstChild(item).IsOk():
            self.CheckItemRecursively(item, state = wx.CHK_UNCHECKED if event.GetOldCheckedState() else wx.CHK_CHECKED)

        self._main_window.updateVideoCountLabel(self.get_checked_item_count())

    def get_checked_item_count(self):
        _count = 0

        item: wx.dataview.TreeListItem = self.GetFirstChild(self.GetRootItem())

        while item.IsOk():
            item = self.GetNextItem(item)

            if item.IsOk():
                if self.GetItemData(item).type == "item" and self.GetCheckedState(item) == wx.CHK_CHECKED:
                    _count += 1

        return _count
    
    def get_all_checked_item(self, video_quality_id: Optional[int] = None):
        def get_item_info(title: str, cid: int):
            match self._main_window.current_parse_type:
                case ParseType.Video:
                    self.get_video_download_info(title, EpisodeInfo.cid_dict.get(cid))

                case ParseType.Bangumi:
                    self.get_bangumi_download_info(title, EpisodeInfo.cid_dict.get(cid))

                case ParseType.Cheese:
                    self.get_cheese_download_info(title, EpisodeInfo.cid_dict.get(cid))

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
    
    def format_info_entry(self, referer_url: str, download_type: int, title: str, duration: int, cover_url: Optional[str] = None, bvid: Optional[str] = None, cid: Optional[int] = None, aid: Optional[int] = None, ep_id: Optional[int] = None):
        def get_download_option():
            if AudioInfo.download_audio_only:
                return DownloadOption.OnlyAudio.value
            else:
                download_info.merge_video_and_audio = True
                return DownloadOption.VideoAndAudio.value

        download_info = DownloadTaskInfo()

        download_info.id = random.randint(10000000, 99999999)

        download_info.title = title
        download_info.cover_url = cover_url
        download_info.referer_url = referer_url
        download_info.bvid = bvid
        download_info.cid = cid
        download_info.aid = aid
        download_info.ep_id = ep_id
        download_info.duration = duration

        download_info.video_quality_id = self.video_quality_id
        download_info.audio_quality_id = AudioInfo.audio_quality_id

        download_info.download_option = get_download_option()

        download_info.download_type = download_type

        download_info.get_danmaku = ExtraInfo.get_danmaku
        download_info.danmaku_type = ExtraInfo.danmaku_type
        download_info.get_cover = ExtraInfo.get_cover
        download_info.get_subtitle = ExtraInfo.get_subtitle
        download_info.subtitle_type = ExtraInfo.subtitle_type

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

        self.download_task_info_list.append(self.format_info_entry(referer_url, ParseType.Video.value, title, duration, cover_url = cover_url, bvid = bvid, cid = cid))
    
    def get_bangumi_download_info(self, title: str, entry: dict):
        cover_url = entry["cover"]
        bvid = entry["bvid"]
        cid = entry["cid"]

        if "duration" in entry:
            duration = entry["duration"] / 1000
        else:
            duration = 0

        referer_url = BangumiInfo.url

        self.download_task_info_list.append(self.format_info_entry(referer_url, ParseType.Bangumi.value, title, duration, cover_url = cover_url, bvid = bvid, cid = cid))
    
    def get_cheese_download_info(self, title: str, entry: dict):
        cover_url = entry["cover"]
        aid = entry["aid"]
        cid = entry["cid"]
        ep_id = entry["id"]
        duration = entry["duration"]

        referer_url = CheeseInfo.url

        self.download_task_info_list.append(self.format_info_entry(referer_url, ParseType.Cheese.value, title, duration, cover_url, cid = cid, aid = aid, ep_id = ep_id))

class ScrolledPanel(_ScrolledPanel):
    def __init__(self, parent, size = wx.DefaultSize):
        _ScrolledPanel.__init__(self, parent, -1, size = size)

        self.sizer = wx.BoxSizer(wx.VERTICAL)

        self.SetSizer(self.sizer)

class InfoBar(wx.InfoBar):
    def __init__(self, parent):
        wx.InfoBar.__init__(self, parent, -1)

    def ShowMessage(self, msg, flags=...):
        super().Dismiss()
        return super().ShowMessage(msg, flags)

class TextCtrl(wx.TextCtrl):
    def __init__(self, *args, **kwargs):

        self.double_click_lock = 0 # 双击锁，防止双击抬起误触发全选

        self.last_click_time = 0 # 上一次双击的时间

        wx.TextCtrl.__init__(self, *args, **kwargs)

        self.Bind_EVT()

    def Bind_EVT(self):
        self.Bind(wx.EVT_LEFT_UP, self.onClickEVT)
        
        self.Bind(wx.EVT_LEFT_DCLICK, self.onDClickEVT)

    def onClickEVT(self, event):
        event.Skip() # 保留原有事件

        if int(time.time() * 1000) - self.last_click_time < 500: # 双击和单击的点击间隔小于 500ms，视为三击
            if self.double_click_lock==0:
                if self.GetSelection()!=(0,-1): # 检查是否已经全选
                    self.SelectAll()
        self.double_click_lock = 0
    
    def onDClickEVT(self, event):
        event.Skip() # 保留原有事件

        self.last_click_time = int(time.time() * 1000)
        self.double_click_lock = 1

class ActionButton(wx.Panel):
    def __init__(self, parent, title):
        self._title = title

        wx.Panel.__init__(self, parent, -1)

        self.init_UI()

        self.Bind_EVT()

        self._active = False
        self._lab_hover = False

    def init_UI(self):
        self.icon = wx.StaticBitmap(self, -1, size = self.FromDIP((16, 16)))

        self.lab = wx.StaticText(self, -1, self._title)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.AddSpacer(50)
        hbox.Add(self.icon, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        hbox.Add(self.lab, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, 10)
        hbox.AddSpacer(50)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.AddSpacer(5)
        vbox.Add(hbox, 0, wx.EXPAND)
        vbox.AddSpacer(5)

        self.SetSizerAndFit(vbox)
    
    def Bind_EVT(self):
        self.Bind(wx.EVT_ENTER_WINDOW, self.onHoverEVT)
        self.Bind(wx.EVT_LEAVE_WINDOW, self.onLeaveEVT)
        self.Bind(wx.EVT_LEFT_DOWN, self.onClickEVT)

        self.lab.Bind(wx.EVT_ENTER_WINDOW, self.onLabHoverEVT)
        self.lab.Bind(wx.EVT_LEAVE_WINDOW, self.onLabLeaveEVT)
        self.lab.Bind(wx.EVT_LEFT_DOWN, self.onClickEVT)

    def onHoverEVT(self, event):
        self.SetBackgroundColour(wx.Colour(220, 220, 220))

        self.Refresh()

        event.Skip()

    def onLabHoverEVT(self, event):
        self._lab_hover = True

        event.Skip()
    
    def onLeaveEVT(self, event):
        if not self._active and not self._lab_hover:
            self.SetBackgroundColour("white")

            self.Refresh()

        event.Skip()

    def onLabLeaveEVT(self, event):
        self._lab_hover = False

        event.Skip()
    
    def onClickEVT(self, event):
        self.SetBackgroundColour(wx.Colour(210, 210, 210))

        self.Refresh()

        self._active = True

        self.onClickCustomEVT()

        event.Skip()
    
    def setActiveState(self):
        self._active = True
        self.SetBackgroundColour(wx.Colour(210, 210, 210))

        self.Refresh()

    def setUnactiveState(self):
        self._active = False
        self.SetBackgroundColour("white")

        self.Refresh()

    def setBitmap(self, bitmap):
        self.icon.SetBitmap(bitmap)

    def setTitle(self, title):
        self.lab.SetLabel(title)

    def onClickCustomEVT(self):
        pass

class InfoLabel(wx.StaticText):
    def __init__(self, parent, label: str = wx.EmptyString, size = wx.DefaultSize):
        wx.StaticText.__init__(self, parent, -1, label, size = size)

        if not Config.Sys.dark_mode:
            self.SetForegroundColour(wx.Colour(108, 108, 108))