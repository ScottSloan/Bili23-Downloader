import wx
import wx.dataview

from utils.config import Config
from utils.tools import *
from utils.video import VideoInfo
from utils.bangumi import BangumiInfo
from utils.live import LiveInfo
from utils.audio import AudioInfo

class Frame(wx.Frame):
    def __init__(self, parent, title, has_panel = True):
        wx.Frame.__init__(self, parent, -1, title)

        self.SetIcon(wx.Icon(Config.res_icon))

        if has_panel: self.panel = wx.Panel(self, -1)

    def dlgbox(self, message, caption, style):
        wx.MessageDialog(self, message, caption, style).ShowModal()
        
class Dialog(wx.Dialog):
    def __init__(self, parent, title, size):
        wx.Dialog.__init__(self, parent, -1, title)

        self.panel = wx.Panel(self, -1)

    def dlgbox(self, message, caption, style):
        wx.MessageDialog(self, message, caption, style).ShowModal()

class ProcessError(Exception):
    pass

class TreeListCtrl(wx.dataview.TreeListCtrl):
    def __init__(self, parent, onError):
        self.onError = onError
        wx.dataview.TreeListCtrl.__init__(self, parent, -1, style = wx.dataview.TL_3STATE)

        self.init_list()

        self.Bind(wx.dataview.EVT_TREELIST_ITEM_CHECKED, self.onCheckItem)

    def init_list(self):
        self.rootitems = self.all_list_items = []

        self.ClearColumns()
        self.DeleteAllItems()
        self.AppendColumn("序号", width = self.FromDIP(75))
        self.AppendColumn("标题", width = self.FromDIP(375))
        self.AppendColumn("备注", width = self.FromDIP(50))
        self.AppendColumn("时长", width = self.FromDIP(75))
    
    def set_video_list(self):
        VideoInfo.multiple = True if len(VideoInfo.pages) > 1 else False

        self.rootitems.append("视频")
        items_content = {}
        
        if VideoInfo.collection:
            items_content["视频"] = [[str(index + 1), value["title"], "", format_duration(value["arc"]["duration"])] for index, value in enumerate(VideoInfo.episodes)]
        else:
            items_content["视频"] = [[str(i["page"]), i["part"] if VideoInfo.multiple else VideoInfo.title, "", format_duration(i["duration"])] for i in VideoInfo.pages]

        ismultiple = True if len(VideoInfo.pages) > 1 or len(VideoInfo.episodes) > 1 else False
        self.append_list(items_content, ismultiple)

    def set_bangumi_list(self):
        items_content = {}

        for key, value in BangumiInfo.sections.items():
            if not Config.show_sections and key != "正片":
                continue

            items_content[key] = [[str(index + 1), format_bangumi_title(episode), episode["badge"], format_duration(episode["duration"])] for index, episode in enumerate(value)]

            self.rootitems.append(key)

        self.append_list(items_content, False)

    def set_live_list(self):
        items_content = {}

        items_content["直播"] = [["1", LiveInfo.title, "", ""]]

        self.rootitems.append("直播")

        self.append_list(items_content, False)
    
    def set_audio_list(self):
        items_content = {}

        if AudioInfo.isplaylist:
            items_content["歌单"] = [[str(index + 1), value["title"], "", format_duration(value["duration"])] for index, value in enumerate(AudioInfo.playlist)]

            self.rootitems.append("歌单")

        else:
            items_content["音乐"] = [["1", AudioInfo.title, "", format_duration(AudioInfo.duration)]]

            self.rootitems.append("音乐")

        self.append_list(items_content, False)

    def append_list(self, items_content: dict, multiple: bool):
        root = self.GetRootItem()
        self.all_list_items = []

        for i in items_content:
            rootitem = self.AppendItem(root, i)
            
            if multiple:
                self.SetItemText(rootitem, 1, VideoInfo.title)
            
            self.all_list_items.append(rootitem)

            for n in items_content[i]:
                childitem = self.AppendItem(rootitem, n[0])
                self.CheckItem(childitem, state = wx.CHK_CHECKED)
                self.all_list_items.append(childitem)

                for i in [1, 2, 3]:
                    self.SetItemText(childitem, i, n[i])

            self.CheckItem(rootitem, state = wx.CHK_CHECKED)
            self.Expand(rootitem)

    def onCheckItem(self, event):
        item = event.GetItem()

        item_text = self.GetItemText(item, 0)
        self.UpdateItemParentStateRecursively(item)

        if item_text in self.rootitems:
            self.CheckItemRecursively(item, state = wx.CHK_UNCHECKED if event.GetOldCheckedState() else wx.CHK_CHECKED)

    def get_allcheckeditem(self, type):
        VideoInfo.down_pages.clear()
        BangumiInfo.down_episodes.clear()
        AudioInfo.down_list.clear()

        for i in self.all_list_items:
            text = self.GetItemText(i, 0)
            state = bool(self.GetCheckedState(i))
            
            if text not in self.rootitems and state:
                item_title = self.GetItemText(i, 1)
                parent_text = self.GetItemText(self.GetItemParent(i), 0)
                
                if type == VideoInfo:
                    index = int(self.GetItemText(i, 0))

                    if VideoInfo.collection:
                        VideoInfo.down_pages.append(VideoInfo.episodes[index - 1])
                    else:
                        VideoInfo.down_pages.append(VideoInfo.pages[index - 1])

                elif type == BangumiInfo:
                    index = [i for i, v in enumerate(BangumiInfo.sections[parent_text]) if v["share_copy"] == item_title][0]
                    BangumiInfo.down_episodes.append(BangumiInfo.sections[parent_text][index])

                elif type == AudioInfo:
                    index = int(self.GetItemText(i, 0))
                    
                    if AudioInfo.isplaylist:
                        AudioInfo.down_list.append(AudioInfo.playlist[index - 1])
                    else:
                        AudioInfo.down_list.append({"id": AudioInfo.sid, "title": AudioInfo.title})

        if len(VideoInfo.down_pages) == 0 and len(BangumiInfo.down_episodes) == 0 and len(AudioInfo.down_list) == 0:
            self.onError(401)
            return False
        else: 
            return True

class InfoBar(wx.InfoBar):
    def __init__(self, parent):
        wx.InfoBar.__init__(self, parent, -1)
    
    def ShowMessage(self, msg, flags=...):
        super().Dismiss()
        return super().ShowMessage(msg, flags)
    
    def _show_message(self, msg: str, flags, flag_code):
        flag_wrap = {0: "错误", 1: "警告", 2: "提示"}

        super().ShowMessage("{}：{}".format(flag_wrap[flag_code], msg), flags)
        raise ProcessError(msg)

    def ShowMessageInfo(self, code: int):
        if code == 400:
            msg = "请求失败，请检查地址是否有误"

            self._show_message(msg, wx.ICON_ERROR, 0)

        elif code == 401:
            msg = "请选择要下载的视频"
            
            self._show_message(msg, wx.ICON_WARNING, 1)

        elif code == 403:
            super().ShowMessage("错误：无法获取视频下载地址", flags = wx.ICON_ERROR)
            raise ProcessError("Failed to download the video")

        elif code == 404:
            msg = "无法获取直播源"

            self._show_message(msg, wx.ICON_ERROR, 0)

        elif code == 405:
            super().ShowMessage("错误：检查更新失败", flags = wx.ICON_ERROR)
            raise ProcessError("Failed to check update")

        if code == 100:
            super().ShowMessage("提示：有新版本更新可用", flags = wx.ICON_INFORMATION)
