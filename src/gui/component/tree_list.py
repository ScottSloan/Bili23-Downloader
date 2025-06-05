import wx
import random
import wx.dataview
from typing import Callable

from utils.config import Config
from utils.common.enums import ParseType, VideoType, Platform
from utils.common.data_type import DownloadTaskInfo, TreeListItemInfo

from utils.parse.video import VideoInfo
from utils.parse.bangumi import BangumiInfo
from utils.parse.audio import AudioInfo
from utils.parse.episode import EpisodeInfo
from utils.parse.cheese import CheeseInfo

class TreeListCtrl(wx.dataview.TreeListCtrl):
    def __init__(self, parent, callback: Callable):
        def get_list_size():
            match Platform(Config.Sys.platform):
                case Platform.Windows:
                    return self.FromDIP((775, 300))
                
                case Platform.Linux | Platform.macOS:
                    return self.FromDIP((775, 350))
        
        from gui.main_v2 import MainWindow

        self.parent: MainWindow = parent.GetParent()
        self.callback = callback

        wx.dataview.TreeListCtrl.__init__(self, parent, -1, style = wx.dataview.TL_3STATE)

        self.SetSize(get_list_size())

        self.Bind_EVT()

        self.init_list()
    
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
                    data.list_number = self.count
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
                    self.count += 1

                    self.SetItemText(item, 0, str(self.count))
                    self.SetItemText(item, 1, data["title"])
                    self.SetItemText(item, 2, data["badge"])
                    self.SetItemText(item, 3, data["duration"])
                    
                    self.SetItemData(item, get_item_data("item", data["title"], data["cid"]))

                    _column_width = self.WidthFor(data["title"])

                    if _column_width > self.title_longest_width:
                        self.title_longest_width = _column_width

                if Config.Misc.auto_select or self.item_count == 1:
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
                        self.item_count += 1

                    for value in data.values():
                        traverse(value)
            
            traverse(EpisodeInfo.data)
        
        self.init_list()

        self.count = 0
        self.title_longest_width = 0
        self.item_count = 0

        get_item_count()

        traverse_item(EpisodeInfo.data, self.GetRootItem())

        if self.title_longest_width > self.FromDIP(375):
            self.SetColumnWidth(1, self.title_longest_width + 15)

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

        self.callback(self.get_checked_item_count())

    def get_checked_item_count(self):
        count = 0

        item: wx.dataview.TreeListItem = self.GetFirstChild(self.GetRootItem())

        while item.IsOk():
            item = self.GetNextItem(item)

            if item.IsOk():
                if self.GetItemData(item).type == "item" and self.GetCheckedState(item) == wx.CHK_CHECKED:
                    count += 1

        return count
    
    def get_all_checked_item(self):
        def get_download_info(list_number: int, title: str, cid: int):
            base_info = self.get_base_download_info(list_number, title, EpisodeInfo.cid_dict.get(cid))

            if Config.Download.stream_download_option:
                self.add_video_type_to_list(base_info)

            if self.download_extra:
                self.add_extra_type_to_list(base_info)

        self.download_task_info_list = []

        item: wx.dataview.TreeListItem = self.GetFirstChild(self.GetRootItem())

        while item.IsOk():
            item = self.GetNextItem(item)

            if item.IsOk():
                if self.GetItemData(item).type == "item" and self.GetCheckedState(item) == wx.CHK_CHECKED:
                    list_number = self.GetItemData(item).list_number
                    title = self.GetItemData(item).title
                    cid = self.GetItemData(item).cid
                    
                    if cid:
                        get_download_info(list_number, title, cid)
    
    def format_info_entry(self, base_info: dict):
        download_info = DownloadTaskInfo()

        download_info.id = random.randint(10000000, 99999999)
        download_info.list_number = base_info.get("list_number")
        download_info.title = base_info.get("title")
        download_info.series = base_info.get("series")
        download_info.cover_url = base_info.get("cover_url")
        download_info.referer_url = base_info.get("referer_url")
        download_info.bvid = base_info.get("bvid")
        download_info.cid = base_info.get("cid")
        download_info.aid = base_info.get("aid")
        download_info.ep_id = base_info.get("ep_id")
        download_info.duration = base_info.get("duration")

        download_info.video_quality_id = base_info.get("video_quality_id")
        download_info.audio_quality_id = base_info.get("audio_quality_id")
        download_info.video_codec_id = base_info.get("video_codec_id")

        download_info.download_option = base_info.get("download_option")
        download_info.download_type = base_info.get("download_type")
        download_info.ffmpeg_merge = base_info.get("ffmpeg_merge", False)

        download_info.extra_option = base_info.get("extra_option", {})

        download_info.pubtime = base_info.get("pubtime")
        download_info.area = base_info.get("area")
        download_info.tname_info = base_info.get("tname_info", {})
        download_info.up_info = base_info.get("up_info", {})

        return download_info

    def get_base_download_info(self, list_number: int, title: str, entry: dict):
        match self.parent.current_parse_type:
            case ParseType.Video:
                info = self.get_video_download_info(title, entry)

            case ParseType.Bangumi:
                info = self.get_bangumi_download_info(title, entry)

            case ParseType.Cheese:
                info = self.get_cheese_download_info(title, entry)

        info["list_number"] = list_number
        info["download_option"] = Config.Download.stream_download_option
                
        return info

    def get_video_download_info(self, title: str, entry: dict):
        match VideoType(VideoInfo.type):
            case VideoType.Single:
                cover_url = VideoInfo.cover
                duration = entry.get("duration")
                aid = VideoInfo.aid
                cid = VideoInfo.cid
                bvid = VideoInfo.bvid
                pubtime = VideoInfo.pubtime

            case VideoType.Part:
                cover_url = VideoInfo.cover
                duration = entry.get("duration")
                aid = VideoInfo.aid
                cid = entry.get("cid")
                bvid = VideoInfo.bvid
                pubtime = VideoInfo.pubtime

            case VideoType.Collection:
                if "arc" in entry:
                    cover_url = entry.get("arc").get("pic")
                    duration = entry.get("arc").get("duration")
                    aid = entry.get("aid")
                    cid = entry.get("cid")
                    bvid = entry.get("bvid")
                    pubtime = entry.get("arc").get("pubdate")
                else:
                    cover_url = entry.get("cover_url")
                    duration = entry.get("duration")
                    aid = entry.get("aid")
                    cid = entry.get("cid")
                    bvid = entry.get("bvid")
                    pubtime = entry.get("pubtime")

        return {
            "cover_url": cover_url,
            "duration": duration,
            "aid": aid,
            "cid": cid,
            "bvid": bvid,
            "pubtime": pubtime,
            "referer_url": VideoInfo.url,
            "title": title,
            "download_type": ParseType.Video.value,
            "tname_info": {
                "tname": VideoInfo.tname,
                "subtname": VideoInfo.subtname
            },
            "up_info": {
                "up_name": VideoInfo.up_name,
                "up_mid": VideoInfo.up_mid
            }
        }

    def get_bangumi_download_info(self, title: str, entry: dict):
        cover_url = entry["cover"]
        aid = entry["aid"]
        bvid = entry["bvid"]
        cid = entry["cid"]
        pubtime = entry["pub_time"]

        if "duration" in entry:
            duration = entry["duration"] / 1000
        else:
            duration = 0

        return {
            "cover_url": cover_url,
            "duration": duration,
            "aid": aid,
            "cid": cid,
            "bvid": bvid,
            "pubtime": pubtime,
            "referer_url": BangumiInfo.url,
            "title": title,
            "series": BangumiInfo.title,
            "download_type": ParseType.Bangumi.value,
            "area": BangumiInfo.area,
            "up_info": {
                "up_name": BangumiInfo.up_name,
                "up_mid": BangumiInfo.up_mid
            }
        }
    
    def get_cheese_download_info(self, title: str, entry: dict):
        cover_url = entry["cover"]
        aid = entry["aid"]
        cid = entry["cid"]
        ep_id = entry["id"]
        duration = entry["duration"]
        pubtime = entry["release_date"]

        return {
            "cover_url": cover_url,
            "duration": duration,
            "aid": aid,
            "cid": cid,
            "ep_id": ep_id,
            "pubtime": pubtime,
            "referer_url": CheeseInfo.url,
            "title": title,
            "download_type": ParseType.Cheese.value,
            "up_info": {
                "up_name": CheeseInfo.up_name,
                "up_mid": CheeseInfo.up_mid
            }
        }

    def add_video_type_to_list(self, info: dict):
        info["video_quality_id"] = self.parent.video_quality_id
        info["audio_quality_id"] = AudioInfo.audio_quality_id
        info["video_codec_id"] = Config.Download.video_codec_id
        info["ffmpeg_merge"] = True

        self.download_task_info_list.append(self.format_info_entry(info))

    def add_extra_type_to_list(self, info: dict):
        info["download_type"] = ParseType.Extra.value
        info["extra_option"] = {
            "download_danmaku_file": Config.Basic.download_danmaku_file,
            "danmaku_file_type": Config.Basic.danmaku_file_type,
            "download_subtitle_file": Config.Basic.download_subtitle_file,
            "subtitle_file_type": Config.Basic.subtitle_file_type,
            "download_cover_file": Config.Basic.download_cover_file
        }
        
        self.download_task_info_list.append(self.format_info_entry(info))

    @property
    def download_extra(self):
        return Config.Basic.download_danmaku_file or Config.Basic.download_subtitle_file or Config.Basic.download_cover_file
