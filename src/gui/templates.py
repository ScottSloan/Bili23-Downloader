import io
import wx
import wx.dataview
from typing import Optional
from wx.lib.scrolledpanel import ScrolledPanel as _ScrolledPanel

from utils.icons import getAppIconSmall
from utils.tools import format_duration, format_bangumi_title, get_new_id, get_legal_name
from utils.config import Config, Download, Audio
from utils.video import VideoInfo
from utils.bangumi import BangumiInfo

class Frame(wx.Frame):
    def __init__(self, parent, title, style = wx.DEFAULT_FRAME_STYLE):
        wx.Frame.__init__(self, parent, -1, title, style = style)

        self.SetIcon(wx.Icon(wx.Image(io.BytesIO(getAppIconSmall())).ConvertToBitmap()))

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

    def set_list(self, video_list: dict):
        root = self.GetRootItem()
        self.all_list_items = []

        for i in video_list:
            rootitem = self.AppendItem(root, i)
            
            self.all_list_items.append(rootitem)

            for n in video_list[i]:
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
        
        if VideoInfo.type == Config.Type.VIDEO_TYPE_SECTIONS:
            for key, value in VideoInfo.sections.items():
                video_list[key] = [[str(index + 1), episode["arc"]["title"], "", format_duration(episode, 0)] for index, episode in enumerate(value)]

                self.parent_items.append(key)
        else:
            self.parent_items.append("视频")
            video_list["视频"] = [[str(index + 1), episode["part"] if VideoInfo.type == 2 else VideoInfo.title, "", format_duration(episode, 1)] for index, episode in enumerate(VideoInfo.pages_list)]

        self.set_list(video_list)
    
    def set_bangumi_list(self):
        bangumi_list = {}

        for key, value in BangumiInfo.sections.items():
            bangumi_list[key] = [[str(index + 1), format_bangumi_title(episode), episode["badge"], format_duration(episode, 2)] for index, episode in enumerate(value)]

            self.parent_items.append(key)

        self.set_list(bangumi_list)

    def onCheckItem(self, event):
        item = event.GetItem()

        self.UpdateItemParentStateRecursively(item)

        if self.GetFirstChild(item).IsOk():
            self.CheckItemRecursively(item, state = wx.CHK_UNCHECKED if event.GetOldCheckedState() else wx.CHK_CHECKED)
    
    def get_all_selected_item(self, video_quality_id: Optional[int] = None):
        self.video_quality_id = video_quality_id
        Download.download_list.clear()
        
        for i in self.all_list_items:
            text = self.GetItemText(i, 0)
            state = bool(self.GetCheckedState(i))
            
            if text not in self.parent_items and state:
                item_title = self.GetItemText(i, 1)
                parent = self.GetItemText(self.GetItemParent(i), 0)
                
                if Download.current_parse_type == Config.Type.VIDEO:
                    self.get_video_download_info(item_title, parent, int(text))

                elif Download.current_parse_type == Config.Type.BANGUMI:
                    self.get_bangumi_download_info(item_title, parent, int(text))
    
    def format_info_entry(self, type: int, title: str, pic: Optional[str] = None, bvid: Optional[str] = None, cid: Optional[int] = None):
        return {
            "id": get_new_id(),
            "index": None,
            "url": VideoInfo.url if Download.current_parse_type == Config.Type.VIDEO else BangumiInfo.url,
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
            "resolution": self.video_quality_id if self.video_quality_id else None,
            "audio_quality": Audio.audio_quality_id,
            "audio_only": Audio.audio_only,
            "codec": None,
            "download_complete": False, # 下载完成标识
            "flag": False,
            "merge_type": 0, # 视频合成类型
        }

    def get_video_download_info(self, item_title: str, parent: str, index: int):
        if VideoInfo.type == Config.Type.VIDEO_TYPE_SECTIONS:
            # 合集
            index = [index for index, value in enumerate(VideoInfo.sections[parent]) if value["arc"]["title"] == item_title][0]

            info_entry = VideoInfo.sections[parent][index]

            title = info_entry["arc"]["title"]
            pic = info_entry["arc"]["pic"]
            bvid = info_entry["bvid"]
            cid = info_entry["cid"]

        else:
            # 分 P 或单个视频
            info_entry = VideoInfo.pages_list[index - 1]

            # 分 P 视频显示每一个标题
            title = info_entry["part"] if VideoInfo.type == 2 else VideoInfo.title

            # 不再以第一帧作为封面
            pic = VideoInfo.cover
                
            bvid = VideoInfo.bvid
            cid = info_entry["cid"]

        Download.download_list.append(self.format_info_entry(Config.Type.VIDEO, title, pic, bvid, cid))
    
    def get_bangumi_download_info(self: str, parent: str, index: int):
        info_entry = BangumiInfo.sections[parent][index - 1]

        title = info_entry["share_copy"] if BangumiInfo.type_id != 2 else format_bangumi_title(info_entry)
        pic = info_entry["cover"]
        bvid = info_entry["bvid"]
        cid = info_entry["cid"]

        Download.download_list.append(info_entry = self.format_info_entry(Config.Type.BANGUMI, title, pic, bvid, cid))

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