import wx
import random
import wx.dataview
from typing import Optional

from utils.config import Config
from utils.common.enums import ParseType, DownloadOption, VideoType
from utils.common.data_type import DownloadTaskInfo, TreeListItemInfo

from utils.parse.video import VideoInfo
from utils.parse.bangumi import BangumiInfo
from utils.parse.audio import AudioInfo
from utils.parse.episode import EpisodeInfo
from utils.parse.cheese import CheeseInfo

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
        def traverse_item(data: list | dict, node):
            def set_item(data: dict):
                def get_item_data(type: str, title: str, cid: int = 0):
                    data = TreeListItemInfo()
                    data.type = type
                    data.title = title
                    data.cid = cid

                    return data

                if "entries" in data:
                    self.SetItemText(item, 0, str(data["title"]))

                    if "collection_title" in data and data["collection_title"]:
                        self.SetItemText(item, 1, data["collection_title"])

                    if "duration" in data and data["duration"]:
                        self.SetItemText(item, 3, data["duration"])

                    self.SetItemData(item, get_item_data("node", data["title"]))
                else:
                    self._index += 1

                    self.SetItemText(item, 0, str(self._index))
                    self.SetItemText(item, 1, data["title"])
                    self.SetItemText(item, 2, data["badge"])
                    self.SetItemText(item, 3, data["duration"])
                    
                    self.SetItemData(item, get_item_data("item", data["title"], data["cid"]))

                    _column_width = self.WidthFor(data["title"])

                    if _column_width > self._title_longest_width:
                        self._title_longest_width = _column_width

                if Config.Misc.auto_select or self._item_count == 1:
                    self.CheckItem(item, wx.CHK_CHECKED)

                self.Expand(node)

            if isinstance(data, list):
                for entry in data:
                    traverse_item(entry, node)

            elif isinstance(data, dict):
                item = self.AppendItem(node, "")
                
                set_item(data)

                for value in data.values():
                    traverse_item(value, item)

        def get_item_count():
            def traverse(data: list | dict):
                if isinstance(data, list):
                    for entry in data:
                        traverse(entry)
                
                elif isinstance(data, dict):
                    if "cid" in data:
                        self._item_count += 1

                    for value in data.values():
                        traverse(value)
            
            traverse(EpisodeInfo.data)
            
        self._index = 0
        self._title_longest_width = 0
        self._item_count = 0

        get_item_count()

        traverse_item(EpisodeInfo.data, self.GetRootItem())

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
    
    def format_info_entry(self, referer_url: str, download_type: int, title: str, duration: int, cover_url: Optional[str] = None, bvid: Optional[str] = None, cid: Optional[int] = None, aid: Optional[int] = None, ep_id: Optional[int] = None, extra_option: Optional[dict] = None):
        def get_download_option():
            if AudioInfo.download_audio_only:
                return DownloadOption.OnlyAudio.value
            else:
                download_info.ffmpeg_merge = True
                return DownloadOption.VideoAndAudio.value

        def get_ffmpeg_merge():
            match ParseType(download_type):
                case ParseType.Video | ParseType.Bangumi | ParseType.Cheese:
                    return True
                
                case ParseType.Extra:
                    return False

        def get_video_quality_id():
            match ParseType(download_type):
                case ParseType.Video | ParseType.Bangumi | ParseType.Cheese:
                    return self.video_quality_id

        def get_audio_quality_id():
            match ParseType(download_type):
                case ParseType.Video | ParseType.Bangumi | ParseType.Cheese:
                    return AudioInfo.audio_quality_id
                
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

        download_info.video_quality_id = get_video_quality_id()
        download_info.audio_quality_id = get_audio_quality_id()

        download_info.download_option = get_download_option()
        download_info.download_type = download_type
        download_info.ffmpeg_merge = get_ffmpeg_merge()

        download_info.extra_option = extra_option

        return download_info

    def get_video_download_info(self, title: str, entry: dict):
        print(entry)
        match VideoType(VideoInfo.type):
            case VideoType.Single:
                cover_url = VideoInfo.cover
                aid = VideoInfo.aid
                cid = VideoInfo.cid
                bvid = VideoInfo.bvid
                duration = entry["duration"]

            case VideoType.Part:
                cover_url = VideoInfo.cover
                aid = VideoInfo.aid
                cid = entry["cid"]
                bvid = VideoInfo.bvid
                duration = entry["duration"]

            case VideoType.Collection:
                if "arc" in entry:
                    cover_url = entry["arc"]["pic"]
                    duration = entry["arc"]["duration"]
                    aid = entry["aid"]
                    cid = entry["cid"]
                    bvid = entry["bvid"]
                else:
                    cover_url = entry["cover_url"]
                    duration = entry["duration"]
                    aid = entry["aid"]
                    cid = entry["cid"]
                    bvid = entry["bvid"]

        referer_url = VideoInfo.url

        self.download_task_info_list.append(self.format_info_entry(referer_url, ParseType.Video.value, title, duration, cover_url = cover_url, aid = aid, bvid = bvid, cid = cid))

        self.get_extra_download_info(referer_url, title, duration, cover_url, aid = aid, bvid = bvid, cid = cid)

    def get_bangumi_download_info(self, title: str, entry: dict):
        cover_url = entry["cover"]
        aid = entry["aid"]
        bvid = entry["bvid"]
        cid = entry["cid"]

        if "duration" in entry:
            duration = entry["duration"] / 1000
        else:
            duration = 0

        referer_url = BangumiInfo.url

        self.download_task_info_list.append(self.format_info_entry(referer_url, ParseType.Bangumi.value, title, duration, cover_url = cover_url, aid = aid, bvid = bvid, cid = cid))

        self.get_extra_download_info(referer_url, title, duration, cover_url, aid = aid, bvid = bvid, cid = cid)
    
    def get_cheese_download_info(self, title: str, entry: dict):
        cover_url = entry["cover"]
        aid = entry["aid"]
        cid = entry["cid"]
        ep_id = entry["id"]
        duration = entry["duration"]

        referer_url = CheeseInfo.url

        self.download_task_info_list.append(self.format_info_entry(referer_url, ParseType.Cheese.value, title, duration, cover_url, cid = cid, aid = aid, ep_id = ep_id))

        self.get_extra_download_info(referer_url, title, duration, cover_url, cid = cid, aid = aid, ep_id = ep_id)

    def get_extra_download_info(self, referer_url: str, title: str, duration: int, cover_url: str, bvid: Optional[str] = None, cid: Optional[int] = None, aid: Optional[int] = None, ep_id: Optional[int] = None):
        if Config.Extra.download_danmaku_file or Config.Extra.download_subtitle_file or Config.Extra.download_cover_file:
            kwargs = {
                "download_danmaku_file": Config.Extra.download_danmaku_file,
                "danmaku_file_type": Config.Extra.danmaku_file_type,
                "download_subtitle_file": Config.Extra.download_subtitle_file,
                "subtitle_file_type": Config.Extra.subtitle_file_type,
                "download_cover_file": Config.Extra.download_cover_file
            }

            self.download_task_info_list.append(self.format_info_entry(referer_url, ParseType.Extra.value, title, duration, cover_url = cover_url, bvid = bvid, cid = cid, aid = aid, ep_id = ep_id, extra_option = kwargs))
