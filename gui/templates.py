import wx
import os
import wx.adv
import wx.dataview

from utils.config import Config
from utils.error import ProcessError
from utils.live import LiveInfo
from utils.video import VideoInfo
from utils.bangumi import BangumiInfo
from utils.tools import format_duration

class Frame(wx.Frame):
    def __init__(self, parent, title, size, defalut_panel = True):
        wx.Frame.__init__(self, parent, -1, title)
        self.SetIcon(wx.Icon(Config.res_logo))

        self.SetSize(self.FromDIP((size)))

        if defalut_panel: self.panel = wx.Panel(self, -1)
        self.__center(parent)

    def __center(self, parent):
        parent_size, parent_pos, self_size = parent.GetSize(), parent.GetPosition(), self.GetSize()
        p_sx, p_sy, p_px, p_py, s_sx, s_sy = parent_size[0], parent_size[1], parent_pos[0], parent_pos[1], self_size[0], self_size[1]

        self.SetPosition((int((p_sx - s_sx) / 2) + p_px, int((p_sy - s_sy) / 2) + p_py))

class Dialog(wx.Dialog):
    def __init__(self, parent, title, size):
        wx.Dialog.__init__(self, parent, -1, title)
        self.SetSize(self.FromDIP((size)))

        self.panel = wx.Panel(self, -1)
        self.__center(parent)
        
    def __center(self, parent):
        parent_size, parent_pos, self_size = parent.GetSize(), parent.GetPosition(), self.GetSize()
        p_sx, p_sy, p_px, p_py, s_sx, s_sy = parent_size[0], parent_size[1], parent_pos[0], parent_pos[1], self_size[0], self_size[1]

        self.SetPosition((int((p_sx - s_sx) / 2) + p_px, int((p_sy - s_sy) / 2) + p_py))

class InfoBar(wx.InfoBar):
    def __init__(self, parent):
        wx.InfoBar.__init__(self, parent, -1)
    
    def ShowMessage(self, msg, flags=...):
        super().Dismiss()
        return super().ShowMessage(msg, flags)
    
    def show_message_info(self, code: int):
        if code == 400:
            super().ShowMessage("错误：请求失败，请检查地址是否有误", flags = wx.ICON_ERROR)
            raise ValueError("Invalid URL")
            
        elif code == 401:
            super().ShowMessage("警告：请选择要下载的视频", flags = wx.ICON_ERROR)
            raise ProcessError("None items selected to download")
        
        elif code == 402:
            super().ShowMessage("错误：获取视频信息失败", flags = wx.ICON_WARNING)
            raise ProcessError("Failed to get the video info")

        elif code == 403:
            super().ShowMessage("错误：无法获取视频下载地址", flags = wx.ICON_ERROR)
            raise ProcessError("Failed to download the video")

        elif code == 404:
            super().ShowMessage("警告：该清晰度需要大会员 Cookie 才能下载，请添加后再试", flags = wx.ICON_WARNING)
            raise ProcessError("Cookie required to continue")

        elif code == 405:
            super().ShowMessage("错误：检查更新失败", flags = wx.ICON_ERROR)
            raise ProcessError("Failed to check update")

        if code == 100:
            super().ShowMessage("提示：有新版本更新可用", flags = wx.ICON_INFORMATION)

        if code == 101:
            super().ShowMessage("注意：尚未添加大会员 Cookie，部分视频可能无法下载", flags = wx.ICON_WARNING)

class Message:
    def Show_Message(parent, code: int):
        if code == 200:
            wx.MessageDialog(parent, "检查更新失败\n\n当前无法检查更新，请稍候再试", "警告", wx.ICON_WARNING).ShowModal()

        if code == 201:
            wx.MessageDialog(parent, "当前没有可用更新", "提示", wx.ICON_INFORMATION).ShowModal()

        if code == 203:
            wx.MessageDialog(parent, "使用帮助\n\nhelp", "使用帮助", wx.ICON_INFORMATION).ShowModal()
        
        if code == 204:
            wx.MessageDialog(parent, "未指定播放器路径\n\n尚未指定播放器路径，请添加路径后再试", "警告", wx.ICON_WARNING).ShowModal()
        
    def Show_Message_Update(parent, info: list):
        dialog = wx.MessageDialog(parent, "有新的更新可用\n\n{}\n\n更新说明：{}\n\n版本：{}".format(info[1], info[2], info[4]), "提示", wx.ICON_INFORMATION | wx.YES_NO)
        dialog.SetYesNoLabels("马上更新", "稍后更新")
        if dialog.ShowModal() == wx.ID_YES:
            import webbrowser
            webbrowser.open(Config.WEBSITE)

    def Show_Notification_Message(parent):
        msg = wx.adv.NotificationMessage("下载完成", "所有任务已下载完成", parent, wx.ICON_INFORMATION)
        msg.MSWUseToasts()
        msg.SetIcon(wx.Icon(Config.res_logo))
        msg.Show(timeout = 5)

class TreeListCtrl(wx.dataview.TreeListCtrl):
    def __init__(self, parent):
        wx.dataview.TreeListCtrl.__init__(self, parent, -1, style = wx.dataview.TL_3STATE)

        self.init_list_lc()

        self.Bind(wx.dataview.EVT_TREELIST_ITEM_CHECKED, self.__check_item_EVT)

    def init_list_lc(self):
        self.rootitems = self.all_list_items = []

        self.ClearColumns()
        self.DeleteAllItems()
        self.AppendColumn("序号", width = self.FromDIP(100))
        self.AppendColumn("标题", width = self.FromDIP(400))
        self.AppendColumn("备注", width = self.FromDIP(50))
        self.AppendColumn("长度", width = self.FromDIP(75))

    def set_video_list(self):
        VideoInfo.multiple = True if len(VideoInfo.pages) > 1 else False

        self.rootitems.append("视频")
        items_content = {}
        
        if VideoInfo.collection:
            items_content["视频"] = [[str(index + 1), value["title"], "", format_duration(value["arc"]["duration"])] for index, value in enumerate(VideoInfo.episodes)]
        else:
            items_content["视频"] = [[str(i["page"]), i["part"] if VideoInfo.multiple else VideoInfo.title, "", format_duration(i["duration"])] for i in VideoInfo.pages]

        ismultiple = True if len(VideoInfo.pages) > 1 or len(VideoInfo.episodes) > 1 else False
        self.__append_list(items_content, ismultiple)

    def set_bangumi_list(self):
        items_content = {}

        for key, value in BangumiInfo.sections.items():
            if not Config.show_sections and key != "正片":
                continue

            items_content[key] = [[str(i["title"]) if i["title"] != "正片" else "1", i["share_copy"] if i["title"] != "正片" else BangumiInfo.title, i["badge"], format_duration(i["duration"])] for i in value]

            self.rootitems.append(key)

        self.__append_list(items_content, False)

    def set_live_list(self):
        items_content = {}

        items_content["直播"] = [["1", LiveInfo.title, "", ""]]

        self.rootitems.append("直播")

        self.__append_list(items_content, False)
        
    def __append_list(self, items_content: dict, ismultiple: bool):
        root = self.GetRootItem()
        self.all_list_items = []

        for i in items_content:
            rootitem = self.AppendItem(root, i)

            if ismultiple:
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

    def __check_item_EVT(self, event):
        item = event.GetItem()
        itemtext = self.GetItemText(item, 0)
        self.UpdateItemParentStateRecursively(item)

        if itemtext in self.rootitems:
            self.CheckItemRecursively(item, state = wx.CHK_UNCHECKED if event.GetOldCheckedState() else wx.CHK_CHECKED)

    def get_all_checked_item(self, theme, on_error) -> bool:
        vip = False
        VideoInfo.down_pages.clear()
        BangumiInfo.down_episodes.clear()

        for i in self.all_list_items:
            text = self.GetItemText(i, 0)
            state = bool(self.GetCheckedState(i))

            if text not in self.rootitems and state:
                itemtitle = self.GetItemText(i, 1)
                parenttext = self.GetItemText(self.GetItemParent(i), 0)
                
                if theme == VideoInfo:
                    index = int(self.GetItemText(i, 0))
                    if VideoInfo.collection:
                        VideoInfo.down_pages.append(VideoInfo.episodes[index - 1])
                    else:
                        VideoInfo.down_pages.append(VideoInfo.pages[index - 1])
                else:
                    index = [i for i, v in enumerate(BangumiInfo.sections[parenttext]) if v["share_copy"] == itemtitle][0]
                    BangumiInfo.down_episodes.append(BangumiInfo.sections[parenttext][index])
                    if BangumiInfo.sections[parenttext][index]["badge"] == "会员":
                        vip = True
        
        if len(VideoInfo.down_pages) == 0 and len(BangumiInfo.down_episodes) == 0:
            on_error(401)
        
        elif vip and Config.cookie_sessdata == "":
            dialog = wx.MessageDialog(self, "确认下载\n\n所选视频中包含大会员视频，在未添加 Cookie 的情况下将跳过下载。\n确认继续吗？", "提示", wx.ICON_INFORMATION | wx.YES_NO)
            if dialog.ShowModal() == wx.ID_NO:
                return True