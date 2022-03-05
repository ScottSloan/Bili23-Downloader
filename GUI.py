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
from utils.tools import format_duration, remove_file
from utils.error import ProcessError

from gui.info import InfoWindow
from gui.download import DownloadWindow
from gui.settings import SettingWindow
from gui.about import AboutWindow
from gui.processing import ProcessingWindow

class MainWindow(wx.Frame):
    def __init__(self, parent):
        wx.Frame.__init__(self, parent, -1, "B站视频下载工具")
        self.SetSize(self.FromDIP((800, 480)))
        self.Center()
        self.panel = wx.Panel(self, -1)

        self.init_controls()
        self.init_list_lc()
        self.Bind_EVT()

        self.select_all = True

    def init_controls(self):
        self.address_lb = wx.StaticText(self.panel, -1, "地址")
        self.address_tc = wx.TextCtrl(self.panel, -1, style = wx.TE_PROCESS_ENTER)
        self.get_button = wx.Button(self.panel, -1, "Get")

        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        hbox1.Add(self.address_lb, 0, wx.ALL | wx.CENTER, 10)
        hbox1.Add(self.address_tc, 1, wx.EXPAND | wx.TOP | wx.BOTTOM, 10)
        hbox1.Add(self.get_button, 0, wx.ALL, 10)

        self.list_lb = wx.StaticText(self.panel, -1, "视频列表")
        self.quality_lb = wx.StaticText(self.panel, -1, "清晰度")
        self.quality_cb = wx.ComboBox(self.panel, -1, style = wx.CB_READONLY | wx.CB_DROPDOWN)

        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        hbox2.Add(self.list_lb, 0, wx.LEFT | wx.CENTER, 10)
        hbox2.AddStretchSpacer(1)
        hbox2.Add(self.quality_lb, 0, wx.CENTER | wx.RIGHT, 10)
        hbox2.Add(self.quality_cb, 0, wx.RIGHT, 10)

        self.list_lc = wx.dataview.TreeListCtrl(self.panel, -1, style = wx.dataview.TL_CHECKBOX)

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
            pass

        elif menuid == 120:
            wx.MessageDialog(self, "使用帮助\n\nhelp", "使用帮助", wx.ICON_INFORMATION).ShowModal()

        elif menuid == 130:
            about_window = AboutWindow(self)
            about_window.ShowWindowModal()

    def OnClose(self, event):
        subprocess.Popen("cd {} && rm cover.*".format(Config._info_base_path), shell = True, stdout = subprocess.PIPE, stderr = subprocess.PIPE)
        remove_file(Config._info_html)

        Main_Thread_Pool.shutdown(wait = False)
        event.Skip()

    def get_url_EVT(self, event):
        url = self.address_tc.GetValue()

        self.quality_cb.Clear()
        self.list_lb.SetLabel("视频")
        self.info_btn.Enable(False)
        self.download_btn.Enable(False)

        VideoInfo.down_pages = BangumiInfo.down_episodes = []

        self.processing_window = ProcessingWindow(self)
        Main_Thread_Pool.submit(self.get_url_thread, url)
        self.processing_window.ShowWindowModal()     

    def get_url_thread(self, url):
        wx.CallAfter(self.init_list_lc)

        if "BV" in url or "av" in url:
            video_parser.parse_url(url, self.on_error)
            self.theme = VideoInfo

            wx.CallAfter(self.set_video_list)
            wx.CallAfter(self.set_quality, VideoInfo)

        elif "ep" in url or "ss" in url or "md" in url:
            bangumi_parser.parse_url(url, self.on_error)
            self.theme = BangumiInfo

            wx.CallAfter(self.set_bangumi_list)
            wx.CallAfter(self.set_quality, BangumiInfo)
        
        else:
            wx.CallAfter(self.on_error, 400)

        wx.CallAfter(self.get_url_finish)
        
    def get_url_finish(self):
        self.download_btn.Enable(True)
        self.info_btn.Enable(True)
        self.processing_window.Hide()

        self.list_lc.SetFocus()

    def set_video_list(self):
        videos = len(VideoInfo.pages)

        VideoInfo.multiple = True if videos > 1 else False

        self.rootitems, self.rootitems_state, self.all_list_items, items_content = ["视频"], [True], [], {}
        
        items_content["视频"] = [[str(i["page"]), i["part"] if VideoInfo.multiple else VideoInfo.title, "", format_duration(i["duration"])] for i in VideoInfo.pages]

        self.append_list(items_content)
        self.list_lb.SetLabel("视频 (共 %d 个)" % videos)

        self.info_btn.SetLabel("视频信息")
        self.download_btn.SetLabel("下载视频")

    def set_bangumi_list(self):
        bangumis = len(BangumiInfo.episodes)

        self.rootitems, self.rootitems_state, self.all_list_items, items_content = [], [], [], {}

        for key, value in BangumiInfo.sections.items():
            if not Config.show_sections and key != "正片":
                continue

            items_content[key] = [[str(i["title"]) if i["title"] != "正片" else "1", i["share_copy"] if i["title"] != "正片" else BangumiInfo.title, i["badge"], format_duration(i["duration"])] for i in value]

            self.rootitems.append(key)
            self.rootitems_state.append(True)

        self.append_list(items_content)

        if BangumiInfo.theme == "番剧":
            self.list_lb.SetLabel("番剧 (正片共 {} 集)".format(bangumis))

        elif BangumiInfo.theme == "电影":
            self.list_lb.SetLabel("电影正片")

        elif BangumiInfo.theme == "纪录片":
            self.list_lb.SetLabel("纪录片 (正片共 {} 集)".format(bangumis))

        self.info_btn.SetLabel(f"{BangumiInfo.theme}信息")
        self.download_btn.SetLabel(f"下载{BangumiInfo.theme}")

    def append_list(self, items_content):
        root = self.list_lc.GetRootItem()

        for i in items_content:
            rootitem = self.list_lc.AppendItem(root, i)

            if self.theme == VideoInfo and len(VideoInfo.pages) != 1:
                self.list_lc.SetItemText(rootitem, 1, VideoInfo.title)
            
            self.all_list_items.append(rootitem)

            for n in items_content[i]:
                childitem = self.list_lc.AppendItem(rootitem, n[0])
                self.list_lc.CheckItem(childitem, state = wx.CHK_CHECKED)
                self.all_list_items.append(childitem)

                self.list_lc.SetItemText(childitem, 1, n[1])
                self.list_lc.SetItemText(childitem, 2, n[2])
                self.list_lc.SetItemText(childitem, 3, n[3])

            self.list_lc.CheckItem(rootitem, state = wx.CHK_CHECKED)
            self.list_lc.Expand(rootitem)

    def set_quality(self, type):
        self.quality_cb.Set(type.quality_desc)
        type.quality = 80 if 80 in type.quality_id else 64
        self.quality_cb.Select(type.quality_id.index(type.quality))

    def select_quality(self, event):
        if self.theme.quality_id[event.GetSelection()] in [120, 116, 112] and Config.cookie_sessdata == "":
            self.quality_cb.Select(self.theme.quality_id.index(80))
            wx.CallAfter(self.on_error, 403)

        self.theme.quality = self.theme.quality_id[event.GetSelection()]

    def download_EVT(self, event):
        self.get_all_checked_item()

        self.download_window = DownloadWindow(self)

        Main_Thread_Pool.submit(self.download_thread)

        self.download_window.ShowWindowModal()

    def download_thread(self):
        if len(VideoInfo.down_pages) == 0 and len(BangumiInfo.down_episodes) == 0:
            wx.CallAfter(self.on_error, 401)

        kwargs = {"on_start":self.on_download_start, "on_download":self.on_downloading, "on_complete":self.on_download_complete, "on_combine":self.on_combine}

        video_parser.get_video_durl(kwargs) if self.theme == VideoInfo else bangumi_parser.get_bangumi_durl(kwargs)

    def Load_info_window_EVT(self, event):
        self.info_window = InfoWindow(self, VideoInfo.title if self.theme == VideoInfo else BangumiInfo.title)
        self.info_window.Show()

    def Load_setting_window_EVT(self, event):
        setting_window = SettingWindow(self)
        setting_window.ShowWindowModal()

    def check_item_EVT(self, event):
        item = event.GetItem()
        text = self.list_lc.GetItemText(item, 0)

        if text in self.rootitems:
            index = self.rootitems.index(text)
            state = self.rootitems_state[index]

            if state == True:
                self.list_lc.CheckItemRecursively(item, state = wx.CHK_UNCHECKED)
                self.rootitems_state[index] = False

            else:
                self.list_lc.CheckItemRecursively(item, state = wx.CHK_CHECKED)
                self.rootitems_state[index] = True

        elif event.GetOldCheckedState():
            parentitem = self.list_lc.GetItemParent(item)
            index2 = self.rootitems.index(self.list_lc.GetItemText(parentitem))
            self.list_lc.CheckItem(parentitem, state = wx.CHK_UNCHECKED)
            self.rootitems_state[index2] = False

    def get_all_checked_item(self):
        for i in self.all_list_items:
            text = self.list_lc.GetItemText(i, 0)
            state = bool(self.list_lc.GetCheckedState(i))

            if text not in self.rootitems and state:
                index = int(self.list_lc.GetItemText(i, 0))
                parenttext = self.list_lc.GetItemText(self.list_lc.GetItemParent(i), 0)

                if self.theme == VideoInfo:
                    VideoInfo.down_pages.append(VideoInfo.pages[index - 1])
                else:
                    BangumiInfo.down_episodes.append(BangumiInfo.sections[parenttext][index - 1])
                    
    def on_error(self, code):
        self.processing_window.Hide()

        if code == 400:
            wx.MessageDialog(self, "请求失败\n\n请检查地址是否有误", "警告", wx.ICON_WARNING).ShowModal()
            raise ValueError("Invalid URL")
            
        elif code == 401:
            wx.MessageDialog(self, "未选择下载项目\n\n请选择要下载的项目", "警告", wx.ICON_WARNING).ShowModal()
            raise ProcessError("None items selected to download")
        
        elif code == 402:
            wx.MessageDialog(self, "无法获取视频清晰度\n\n需要大会员 Cookie 才能继续", "警告", wx.ICON_WARNING).ShowModal()
            raise ProcessError("Cookie required to continue")

        elif code == 403:
            wx.MessageDialog(self, "需要大会员 Cookie\n\n该清晰度需要大会员 Cookie 才能下载，请添加后再试", "警告", wx.ICON_WARNING).ShowModal()
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

    def on_download_complete(self, message: str):
        wx.CallAfter(self.download_window.Hide)

        dlg = wx.MessageDialog(self, "下载完成\n\n{}".format(message), "提示", wx.ICON_INFORMATION)
        dlg.SetYesNoLabels("打开所在位置", "确定")
        if dlg.ShowModal() == wx.ID_YES:
            os.startfile(Config.download_path)

    def on_combine(self, title: str):
        self.download_window.gauge.Pulse()
        self.download_window.lb.SetLabel("正在合成视频......")

        self.download_window.speed_lb.SetLabel("速度：-")
        self.download_window.size_lb.SetLabel("大小：-")

if __name__ == "__main__":
    app = wx.App()
    
    Main_Thread_Pool = ThreadPoolExecutor(max_workers = 2)

    video_parser = VideoParser()
    bangumi_parser = BangumiParser()

    main_window = MainWindow(None)
    main_window.Show()

    app.MainLoop()