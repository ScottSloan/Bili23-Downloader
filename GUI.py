import wx
import os
import wx.adv
import wx.html2
import subprocess
import wx.dataview
from concurrent.futures import ThreadPoolExecutor

from utils.video import VideoInfo, VideoParser
from utils.bangumi import BangumiInfo, BangumiParser
from utils.config import Config
from utils.tools import format_duration, remove_file, process_shortlink, check_update
from utils.error import ProcessError

from gui.info import InfoWindow
from gui.download import DownloadWindow
from gui.settings import SettingWindow
from gui.about import AboutWindow
from gui.processing import ProcessingWindow
from gui.template import InfoBar

class MainWindow(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, -1, "Bili23 Downloader")

        self.SetIcon(wx.Icon(Config._logo))
        self.SetSize(self.FromDIP((800, 480)))
        self.Center()
        self.panel = wx.Panel(self, -1)

        self.init_controls()
        self.init_list_lc()
        self.Bind_EVT()

        Main_ThreadPool.submit(self.check_app_update)

    def init_controls(self):
        self.infobar = InfoBar(self.panel)

        self.address_lb = wx.StaticText(self.panel, -1, "地址")
        self.address_tc = wx.TextCtrl(self.panel, -1, style = wx.TE_PROCESS_ENTER)
        self.get_button = wx.Button(self.panel, -1, "Get")

        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        hbox1.Add(self.address_lb, 0, wx.ALL | wx.CENTER, 10)
        hbox1.Add(self.address_tc, 1, wx.EXPAND | wx.TOP | wx.BOTTOM, 10)
        hbox1.Add(self.get_button, 0, wx.ALL, 10)

        self.list_lb = wx.StaticText(self.panel, -1, "视频")
        self.quality_lb = wx.StaticText(self.panel, -1, "清晰度")
        self.quality_cb = wx.Choice(self.panel, -1)

        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        hbox2.Add(self.list_lb, 0, wx.LEFT | wx.CENTER, 10)
        hbox2.AddStretchSpacer(1)
        hbox2.Add(self.quality_lb, 0, wx.CENTER | wx.RIGHT, 10)
        hbox2.Add(self.quality_cb, 0, wx.RIGHT, 10)

        self.list_lc = wx.dataview.TreeListCtrl(self.panel, -1, style = wx.dataview.TL_3STATE)

        self.info_btn = wx.Button(self.panel, -1, "视频信息", size = self.FromDIP((90, 30)))
        self.info_btn.Enable(False)
        self.set_btn = wx.Button(self.panel, -1, "设置", size = self.FromDIP((80, 30)))
        self.download_btn = wx.Button(self.panel, -1, "下载视频", size = self.FromDIP((90, 30)))
        self.download_btn.Enable(False)

        hbox3 = wx.BoxSizer(wx.HORIZONTAL)
        hbox3.Add(self.info_btn, 0, wx.BOTTOM | wx.LEFT, 10)
        hbox3.AddStretchSpacer(1)
        hbox3.Add(self.set_btn, 0, wx.BOTTOM, 10)
        hbox3.Add(self.download_btn, 0, wx.ALL & (~wx.TOP), 10)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.infobar, 0, wx.EXPAND)
        vbox.Add(hbox1, 0, wx.EXPAND, 10)
        vbox.Add(hbox2, 0, wx.EXPAND)
        vbox.Add(self.list_lc, 1, wx.EXPAND | wx.ALL, 10)
        vbox.Add(hbox3, 0, wx.EXPAND)

        self.panel.SetSizer(vbox)

        self.init_menu_bar()

    def init_list_lc(self):
        self.list_lc.ClearColumns()
        self.list_lc.DeleteAllItems()
        self.list_lc.AppendColumn("序号", width = self.FromDIP(100))
        self.list_lc.AppendColumn("标题", width = self.FromDIP(400))
        self.list_lc.AppendColumn("备注", width = self.FromDIP(50))
        self.list_lc.AppendColumn("长度", width = self.FromDIP(75))

    def init_menu_bar(self):
        self.menu_bar = wx.MenuBar()
        self.about_menu = wx.Menu()
        self.tool_menu = wx.Menu()

        self.check_menuitem = wx.MenuItem(self.about_menu, 110, "检查更新(&U)")
        self.help_menuitem = wx.MenuItem(self.about_menu, 120, "使用帮助(&C)")
        self.about_menuitem = wx.MenuItem(self.about_menu, 130, "关于(&A)")

        self.menu_bar.Append(self.about_menu,"帮助(&H)")

        self.about_menu.Append(self.check_menuitem)
        self.about_menu.AppendSeparator()
        self.about_menu.Append(self.help_menuitem)
        self.about_menu.Append(self.about_menuitem)

        self.SetMenuBar(self.menu_bar)

    def Bind_EVT(self):
        self.Bind(wx.EVT_CLOSE, self.OnClose)
        self.about_menu.Bind(wx.EVT_MENU, self.menu_EVT)

        self.address_tc.Bind(wx.EVT_TEXT_ENTER, self.get_url_EVT)
        self.get_button.Bind(wx.EVT_BUTTON, self.get_url_EVT)

        self.quality_cb.Bind(wx.EVT_COMBOBOX, self.select_quality)
        self.info_btn.Bind(wx.EVT_BUTTON, self.Load_info_window_EVT)
        self.set_btn.Bind(wx.EVT_BUTTON, self.Load_setting_window_EVT)
        self.download_btn.Bind(wx.EVT_BUTTON, self.download_EVT)

        self.list_lc.Bind(wx.dataview.EVT_TREELIST_ITEM_CHECKED, self.check_item_EVT)

    def menu_EVT(self, event):
        menuid = event.GetId()

        if menuid == 110:
            info = self.update_info
            dialog = wx.MessageDialog(self, "有新的更新可用\n\n{}\n\n更新说明：{}\n\n版本：{}".format(info[1], info[2], info[4]), "提示", wx.ICON_INFORMATION | wx.YES_NO)
            dialog.SetYesNoLabels("马上更新", "稍后更新")
            if dialog.ShowModal() == wx.ID_YES:
                import webbrowser
                webbrowser.open(Config._website)

        elif menuid == 120:
            wx.MessageDialog(self, "使用帮助\n\nhelp", "使用帮助", wx.ICON_INFORMATION).ShowModal()

        elif menuid == 130:
            about_window = AboutWindow(self)

    def OnClose(self, event):
        subprocess.Popen("cd {} && {} cover.*".format(Config._info_base_path, Config._del_cmd), shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        remove_file(Config._info_html)

        event.Skip()

    def get_url_EVT(self, event):
        url = self.address_tc.GetValue()

        self.quality_cb.Clear()
        self.list_lb.SetLabel("视频")
        self.info_btn.Enable(False)
        self.download_btn.Enable(False)

        VideoInfo.down_pages = BangumiInfo.down_episodes = []

        self.processing_window = ProcessingWindow(self)

        Main_ThreadPool.submit(self.get_url_thread, url)

        self.processing_window.ShowWindowModal()
        
    def get_url_thread(self, url: str):
        wx.CallAfter(self.init_list_lc)

        if "b23.tv" in url:
            url = process_shortlink(url)

        if "BV" in url or "av" in url:
            self.theme = VideoInfo
            video_parser.parse_url(url, self.on_redirect, self.on_error)

            self.set_video_list()
            self.set_quality(VideoInfo)

        elif "ep" in url or "ss" in url or "md" in url:
            self.theme = BangumiInfo
            bangumi_parser.parse_url(url, self.on_error)

            self.set_bangumi_list()
            self.set_quality(BangumiInfo)
        
        else:
            self.on_error(400)

        wx.CallAfter(self.get_url_finish)
        
    def get_url_finish(self):
        self.download_btn.Enable(True)
        self.info_btn.Enable(True)
        self.processing_window.Hide()

        self.list_lc.SetFocus()

        if Config.cookie_sessdata == "":
            self.infobar.ShowMessage("注意：尚未添加大会员 Cookie ，部分视频可能无法下载", flags = wx.ICON_WARNING)

    def set_video_list(self):
        videos = len(VideoInfo.episodes) if VideoInfo.collection else len(VideoInfo.pages)

        VideoInfo.multiple = True if len(VideoInfo.pages) > 1 else False

        self.rootitems, self.all_list_items, items_content = ["视频"], [], {}
        
        if VideoInfo.collection:
            items_content["视频"] = [[str(index + 1), value["title"], "", format_duration(value["arc"]["duration"])] for index, value in enumerate(VideoInfo.episodes)]
        else:
            items_content["视频"] = [[str(i["page"]), i["part"] if VideoInfo.multiple else VideoInfo.title, "", format_duration(i["duration"])] for i in VideoInfo.pages]

        self.append_list(items_content)
        self.list_lb.SetLabel("视频 (共 %d 个)" % videos)

    def set_bangumi_list(self):
        bangumis = len(BangumiInfo.episodes)

        self.rootitems, self.all_list_items, items_content = [], [], {}

        for key, value in BangumiInfo.sections.items():
            if not Config.show_sections and key != "正片":
                continue

            items_content[key] = [[str(i["title"]), i["share_copy"] if i["title"] != "正片" else BangumiInfo.title, i["badge"], format_duration(i["duration"])] for i in value]

            self.rootitems.append(key)

        self.append_list(items_content)

        self.list_lb.SetLabel("{} (正片共 {} 集)".format(BangumiInfo.theme, bangumis))

    def append_list(self, items_content):
        root = self.list_lc.GetRootItem()

        for i in items_content:
            rootitem = self.list_lc.AppendItem(root, i)

            if self.theme == VideoInfo and (len(VideoInfo.pages) > 1 or len(VideoInfo.episodes) > 1):
                self.list_lc.SetItemText(rootitem, 1, VideoInfo.title)
            
            self.all_list_items.append(rootitem)

            for n in items_content[i]:
                childitem = self.list_lc.AppendItem(rootitem, n[0])
                self.list_lc.CheckItem(childitem, state = wx.CHK_CHECKED)
                self.all_list_items.append(childitem)

                for i in [1, 2, 3]:
                    self.list_lc.SetItemText(childitem, i, n[i])

            self.list_lc.CheckItem(rootitem, state = wx.CHK_CHECKED)
            self.list_lc.Expand(rootitem)

    def set_quality(self, type):
        self.quality_cb.Set(type.quality_desc)
        type.quality = Config.default_quality if Config.default_quality in type.quality_id else type.quality_id[0]
        self.quality_cb.Select(type.quality_id.index(type.quality))

    def select_quality(self, event):
        if self.theme.quality_id[event.GetSelection()] in [120, 116, 112] and Config.cookie_sessdata == "":
            self.quality_cb.Select(self.theme.quality_id.index(80))
            wx.CallAfter(self.on_error, 403)

        self.theme.quality = self.theme.quality_id[event.GetSelection()]

    def download_EVT(self, event):
        self.get_all_checked_item()

        self.download_window = DownloadWindow(self)

        Main_ThreadPool.submit(self.download_thread)

        self.download_window.ShowWindowModal()

    def download_thread(self):
        kwargs = {"on_start":self.on_download_start, "on_download":self.on_downloading, "on_complete":self.on_download_complete, "on_merge":self.on_merge}

        video_parser.get_video_durl(kwargs) if self.theme == VideoInfo else bangumi_parser.get_bangumi_durl(kwargs)

    def Load_info_window_EVT(self, event):
        self.info_window = InfoWindow(self, VideoInfo.title if self.theme == VideoInfo else BangumiInfo.title)
        self.info_window.Show()

    def Load_setting_window_EVT(self, event):
        setting_window = SettingWindow(self)
        setting_window.ShowWindowModal()

    def check_item_EVT(self, event):
        item = event.GetItem()
        self.list_lc.UpdateItemParentStateRecursively(item)

        if self.list_lc.GetItemText(item, 0) in self.rootitems:
            self.list_lc.CheckItemRecursively(item, state = wx.CHK_UNCHECKED if event.GetOldCheckedState() else wx.CHK_CHECKED)

    def get_all_checked_item(self):
        for i in self.all_list_items:
            text = self.list_lc.GetItemText(i, 0)
            state = bool(self.list_lc.GetCheckedState(i))

            if text not in self.rootitems and state:
                itemtitle = self.list_lc.GetItemText(i, 1)
                parenttext = self.list_lc.GetItemText(self.list_lc.GetItemParent(i), 0)
                
                if self.theme == VideoInfo:
                    index = int(self.list_lc.GetItemText(i, 0))
                    if VideoInfo.collection:
                        VideoInfo.down_pages.append(VideoInfo.episodes[index - 1])
                    else:
                        VideoInfo.down_pages.append(VideoInfo.pages[index - 1])
                else:
                    index = [i for i, v in enumerate(BangumiInfo.sections[parenttext]) if v["share_copy"] == itemtitle][0]
                    BangumiInfo.down_episodes.append(BangumiInfo.sections[parenttext][index])
        
        if len(VideoInfo.down_pages) == 0 and len(BangumiInfo.down_episodes) == 0:
            self.on_error(401)

    def on_error(self, code):
        wx.CallAfter(self.processing_window.Hide)

        if code == 400:
            self.infobar.ShowMessage("请求失败：请检查地址是否有误", flags = wx.ICON_ERROR)
            raise ValueError("Invalid URL")
            
        elif code == 401:
            self.infobar.ShowMessage("未选择下载项目：请选择要下载的项目", flags = wx.ICON_ERROR)
            raise ProcessError("None items selected to download")
        
        elif code == 402:
            self.infobar.ShowMessage("无法获取视频清晰度\n\n需要大会员 Cookie 才能继续", flags = wx.ICON_WARNING)
            raise ProcessError("Cookie required to continue")

        elif code == 403:
            self.infobar.ShowMessage("需要大会员 Cookie：该清晰度需要大会员 Cookie 才能下载，请添加后再试", flags = wx.ICON_WARNING)
            raise ProcessError("Cookie required to continue")

    def on_download_start(self, size: str, index: list, file_name: str, title: str):
        self.download_window.SetTitle("当前第 {} 个，共 {} 个".format(index[0], index[1]))

        down_type = "视频" if file_name.endswith("mp4") else "音频"
        self.download_window.lb.SetLabel("正在下载{}：{}".format(down_type, title))
        self.download_window.size_lb.SetLabel("大小：{}".format(size))

    def on_downloading(self, progress: int, speed: str):
        self.download_window.gauge.SetValue(progress)
        self.download_window.progress_lb.SetLabel("{}%".format(progress))

        self.download_window.speed_lb.SetLabel("速度：{}".format(speed))

    def on_download_complete(self):
        wx.CallAfter(self.download_window.Hide)

        dlg = wx.MessageDialog(self, "下载完成\n\n所选视频已全部下载完成", "提示", wx.ICON_INFORMATION | wx.YES_NO)
        dlg.SetYesNoLabels("打开所在位置", "确定")
        if dlg.ShowModal() == wx.ID_YES:
            os.startfile(Config.download_path)

    def on_merge(self):
        self.download_window.gauge.Pulse()
        self.download_window.lb.SetLabel("正在合成视频......")

        self.download_window.progress_lb.SetLabel("--%")
        self.download_window.speed_lb.SetLabel("速度：-")
        self.download_window.size_lb.SetLabel("大小：-")

    def on_redirect(self, url: str):
        Main_ThreadPool = ThreadPoolExecutor(max_workers = 2)
        Main_ThreadPool.submit(self.get_url_thread, url)

    def check_app_update(self):
        if not Config.auto_check_update:
            return
            
        self.update_info = check_update()

        if self.update_info == None:
            self.infobar.ShowMessage("检查更新失败", wx.ICON_ERROR)

        elif self.update_info[0]:
            self.infobar.ShowMessage("有新版本更新可用", wx.ICON_INFORMATION)

if __name__ == "__main__":
    app = wx.App()

    Main_ThreadPool = ThreadPoolExecutor(max_workers = 2)
    
    video_parser = VideoParser()
    bangumi_parser = BangumiParser()

    main_window = MainWindow(None)
    main_window.Show()

    app.MainLoop()