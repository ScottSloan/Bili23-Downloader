import io
import wx
import wx.dataview
from wx.lib.scrolledpanel import ScrolledPanel as _ScrolledPanel

from utils.icons import get_app_icon
from utils.tools import *
from utils.config import Config, Download
from utils.video import VideoInfo
from utils.bangumi import BangumiInfo

class Frame(wx.Frame):
    def __init__(self, parent, title, style = wx.DEFAULT_FRAME_STYLE):
        wx.Frame.__init__(self, parent, -1, title, style = style)

        self.SetIcon(wx.Icon(wx.Image(io.BytesIO(get_app_icon())).ConvertToBitmap()))

        self.panel = wx.Panel(self)

class TreeListCtrl(wx.dataview.TreeListCtrl):
    def __init__(self, parent):
        wx.dataview.TreeListCtrl.__init__(self, parent, -1, style = wx.dataview.TL_3STATE)

        self.Bind_EVT()

        self.init_list()
    
    def Bind_EVT(self):
        self.Bind(wx.dataview.EVT_TREELIST_ITEM_CHECKED, self.onCheckItem)

    def init_list(self):
        self.parent_items = []

        self.ClearColumns()
        self.DeleteAllItems()
        
        self.AppendColumn("序号", width = self.FromDIP(85))
        self.AppendColumn("标题", width = self.FromDIP(375))
        self.AppendColumn("备注", width = self.FromDIP(50))
        self.AppendColumn("时长", width = self.FromDIP(75))

    def set_list(self, list: dict):
        root = self.GetRootItem()
        self.all_list_items = []

        for i in list:
            rootitem = self.AppendItem(root, i)
            
            self.all_list_items.append(rootitem)

            for n in list[i]:
                childitem = self.AppendItem(rootitem, n[0])

                if Config.Misc.auto_select:
                    self.CheckItem(childitem, state = wx.CHK_CHECKED)

                self.all_list_items.append(childitem)

                for i in [1, 2, 3]:
                    self.SetItemText(childitem, i, n[i])

            if Config.Misc.auto_select:
                self.CheckItem(rootitem, state = wx.CHK_CHECKED)
                
            self.Expand(rootitem)

    def set_video_list(self):
        video_list = {}
        
        if VideoInfo.type == 3:
            for key, value in VideoInfo.sections.items():
                video_list[key] = [[str(index + 1), episode["arc"]["title"], "", format_duration(episode["arc"]["duration"])] for index, episode in enumerate(value)]

                self.parent_items.append(key)
        else:
            self.parent_items.append("视频")
            video_list["视频"] = [[str(index + 1), episode["part"] if VideoInfo.type == 2 else VideoInfo.title, "", format_duration(episode["duration"])] for index, episode in enumerate(VideoInfo.pages)]

        self.set_list(video_list)
    
    def set_bangumi_list(self):
        bangumi_list = {}

        for key, value in BangumiInfo.sections.items():
            if Config.Misc.show_episodes != 2 and key != "正片":
                continue

            bangumi_list[key] = [[str(index + 1), format_bangumi_title(episode), episode["badge"], format_duration(episode["duration"], bangumi = True)] for index, episode in enumerate(value)]

            self.parent_items.append(key)

        self.set_list(bangumi_list)

    def onCheckItem(self, event):
        item = event.GetItem()

        self.UpdateItemParentStateRecursively(item)

        if self.GetFirstChild(item).IsOk():
            self.CheckItemRecursively(item, state = wx.CHK_UNCHECKED if event.GetOldCheckedState() else wx.CHK_CHECKED)
    
    def get_all_selected_item(self, resolution: int = None):
        self.resolution = resolution
        Download.download_list.clear()
        
        for i in self.all_list_items:
            text = self.GetItemText(i, 0)
            state = bool(self.GetCheckedState(i))
            
            if text not in self.parent_items and state:
                item_title = self.GetItemText(i, 1)
                parent = self.GetItemText(self.GetItemParent(i), 0)
                
                if Download.current_type == VideoInfo:
                    self.get_video_download_info(item_title, parent, int(text))
                elif Download.current_type == BangumiInfo:
                    self.get_bangumi_download_info(item_title, parent, int(text))
    
    def get_video_download_info(self, item_title: str, parent: str, index: int):
        if VideoInfo.type == 3:
            index = [index for index, value in enumerate(VideoInfo.sections[parent]) if value["arc"]["title"] == item_title][0]

            info_entry = VideoInfo.sections[parent][index]

            title = info_entry["arc"]["title"]
            pic = info_entry["arc"]["pic"]
            bvid = info_entry["bvid"]
            cid = info_entry["cid"]

        else:
            info_entry = VideoInfo.pages[index - 1]

            title = info_entry["part"] if VideoInfo.type == 2 else VideoInfo.title
            pic = info_entry["first_frame"] if "first_frame" in info_entry else VideoInfo.cover
            bvid = VideoInfo.bvid
            cid = info_entry["cid"]

        Download.download_list.append(self.format_info_entry(Config.Type.VIDEO, title, pic, bvid, cid))
    
    def get_bangumi_download_info(self, item_title: str, parent: str, index: int):
        info_entry = BangumiInfo.sections[parent][index - 1]

        title = info_entry["share_copy"] if BangumiInfo.type != "电影" else format_bangumi_title(info_entry)
        pic = info_entry["cover"]
        bvid = info_entry["bvid"]
        cid = info_entry["cid"]

        Download.download_list.append(self.format_info_entry(Config.Type.BANGUMI, title, pic, bvid, cid))

    def format_info_entry(self, type: int, title: str, pic: str, bvid: str = None, cid: str = None):
        return {
            "id": get_new_id(),
            "url": VideoInfo.url if Download.current_type == VideoInfo else BangumiInfo.url,
            "type": type,
            "bvid": bvid,
            "cid": cid,
            "title": get_legal_name(title),
            "pic": pic,
            "size": None,
            "total_size": None,
            "complete": None,
            "completed_size": None,
            "progress": 0,
            "status": "wait",
            "resolution": self.resolution if self.resolution else None,
            "codec": None,
            "flag": False
        }

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
