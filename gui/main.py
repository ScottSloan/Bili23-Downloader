import wx
import os
import datetime
from threading import Thread

from .templates import Frame, TreeListCtrl, InfoBar
from .about import AboutWindow
from .processing import ProcessingWindow
from .login import LoginWindow
from .user import UserWindow
from .settings import SettingWindow
from .download import DownloadWindow
from .debug import DebugWindow

from utils.config import Config
from utils.tools import process_shortlink, find_str, check_update, get_face_pic, quality_wrap
from utils.video import VideoInfo, VideoParser
from utils.bangumi import BangumiInfo, BangumiParser


class MainWindow(Frame):
    def __init__(self, parent):
        Frame.__init__(self, parent, Config.app_name)

        self.init_UI()

        self.Bind_EVT()

        self.CenterOnParent()

        self.init_parser()

        wx.CallAfter(self.init_userinfo)

        self.check_ffmpeg()

        self.check_login()

    def init_parser(self):
        # 初始化 VideoParser 和 BangumiParser
        self.video_parser = VideoParser(self.onError, self.onRedirect)
        self.bangumi_parser = BangumiParser(self.onError)

        # 设置焦点
        wx.CallAfter(self.treelist.SetFocus)

        self.show_download_window = False
        
    def init_userinfo(self):
        # 显示用户信息
        # 判断是否登录
        if Config.user_name != "":
            # 获取头像
            face = wx.Image(get_face_pic(Config.user_face)).Scale(36, 36)

            self.face.Show()
            self.face.SetBitmap(wx.Bitmap(face, wx.BITMAP_SCREEN_DEPTH))

            # 显示用户名
            self.uname_lab.SetLabel(Config.user_name)
        else:
            self.face.Hide()

            self.uname_lab.SetLabel("未登录")
        
        self.userinfo_hbox.Layout()

        self.vbox.Layout()
    
    def init_UI(self):
        # 信息提示栏
        self.infobar = InfoBar(self.panel)

        # 地址栏
        url_hbox = wx.BoxSizer(wx.HORIZONTAL)

        url_lab = wx.StaticText(self.panel, -1, "地址")
        self.url_box = wx.TextCtrl(self.panel, -1, style = wx.TE_PROCESS_ENTER)
        self.get_btn = wx.Button(self.panel, -1, "Get")

        url_hbox.Add(url_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        url_hbox.Add(self.url_box, 1, wx.EXPAND | wx.ALL & ~(wx.LEFT), 10)
        url_hbox.Add(self.get_btn, 0, wx.ALL & ~(wx.LEFT) | wx.ALIGN_CENTER, 10)

        # 清晰度栏
        quality_hbox = wx.BoxSizer(wx.HORIZONTAL)

        self.type_lab = wx.StaticText(self.panel, -1, "视频")
        quality_lab = wx.StaticText(self.panel, -1, "清晰度")
        self.quality_choice = wx.Choice(self.panel, -1)

        quality_hbox.Add(self.type_lab, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 10)
        quality_hbox.AddStretchSpacer()
        quality_hbox.Add(quality_lab, 0, wx.LEFT | wx.RIGHT | wx.ALIGN_CENTER, 10)
        quality_hbox.Add(self.quality_choice, 0, wx.RIGHT | wx.ALIGN_CENTER, 10)

        # 视频列表
        self.treelist = TreeListCtrl(self.panel, self.onError)
        self.treelist.SetSize(self.FromDIP((800, 260)))

        # 底栏
        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)

        self.download_mgr_btn = wx.Button(self.panel, -1, "下载管理", size = self.FromDIP((90, 30)))
        self.download_btn = wx.Button(self.panel, -1, "下载视频", size = self.FromDIP((90, 30)))
        self.download_btn.Enable(False)
        
        # 用户信息
        self.userinfo_hbox = wx.BoxSizer(wx.HORIZONTAL)

        self.face = wx.StaticBitmap(self.panel, -1)
        self.face.Cursor = wx.Cursor(wx.CURSOR_HAND)
        self.uname_lab = wx.StaticText(self.panel, -1, "用户名")
        self.uname_lab.Cursor = wx.Cursor(wx.CURSOR_HAND)

        self.userinfo_hbox.Add(self.face, 0, wx.ALL & ~(wx.TOP) & ~(wx.RIGHT), 10)
        self.userinfo_hbox.Add(self.uname_lab, 0, wx.ALL & ~(wx.TOP) | wx.ALIGN_CENTER, 10)

        bottom_hbox.Add(self.userinfo_hbox, 0, wx.EXPAND)
        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(self.download_mgr_btn, 0, wx.ALL & ~(wx.TOP), 10)
        bottom_hbox.Add(self.download_btn, 0, wx.ALL & ~(wx.TOP) & ~(wx.LEFT), 10)

        # 窗口 Sizer
        self.vbox = wx.BoxSizer(wx.VERTICAL)

        self.vbox.Add(self.infobar, 1, wx.EXPAND)
        self.vbox.Add(url_hbox, 0, wx.EXPAND)
        self.vbox.Add(quality_hbox, 0, wx.EXPAND)
        self.vbox.Add(self.treelist, 1, wx.ALL | wx.EXPAND, 10)
        self.vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.panel.SetSizer(self.vbox)
        self.init_menubar()

        # 适应窗口大小
        self.vbox.Fit(self)

    def init_menubar(self):
        menu_bar = wx.MenuBar()
        self.help_menu = wx.Menu()
        self.tool_menu = wx.Menu()

        check_menuitem = wx.MenuItem(self.help_menu, 100, "检查更新(&U)")
        log_menuitem = wx.MenuItem(self.help_menu, 110, "更新日志(&L)")
        help_menuitem = wx.MenuItem(self.help_menu, 120, "使用帮助(&C)")
        about_menuitem = wx.MenuItem(self.help_menu, 130, "关于(&A)")

        user_menuitem = wx.MenuItem(self.tool_menu, 200, "用户中心(&E)")
        option_menuitem = wx.MenuItem(self.tool_menu, 210, "设置(&S)")
        debug_menuitem = wx.MenuItem(self.tool_menu, 220, "调试(&D)")
        
        menu_bar.Append(self.tool_menu, "工具(&T)")
        menu_bar.Append(self.help_menu, "帮助(&H)")

        self.tool_menu.Append(user_menuitem)
        self.tool_menu.AppendSeparator()
        self.tool_menu.Append(option_menuitem)
        self.tool_menu.Append(debug_menuitem)

        self.help_menu.Append(check_menuitem)
        self.help_menu.Append(log_menuitem)
        self.help_menu.AppendSeparator()
        self.help_menu.Append(help_menuitem)
        self.help_menu.Append(about_menuitem)

        self.SetMenuBar(menu_bar)
    
    def Bind_EVT(self):
        # 绑定事件
        self.Bind(wx.EVT_MENU, self.menu_EVT)

        self.url_box.Bind(wx.EVT_TEXT_ENTER, self.get_btn_EVT)
        
        self.url_box.Bind(wx.EVT_SET_FOCUS, self.onSetFoucus)
        self.url_box.Bind(wx.EVT_KILL_FOCUS, self.onKillFocus)

        self.get_btn.Bind(wx.EVT_BUTTON, self.get_btn_EVT)
        
        self.uname_lab.Bind(wx.EVT_LEFT_DOWN, self.userinfo_EVT)
        self.face.Bind(wx.EVT_LEFT_DOWN, self.userinfo_EVT)

        self.download_mgr_btn.Bind(wx.EVT_BUTTON, self.download_mgr_btn_EVT)
        self.download_btn.Bind(wx.EVT_BUTTON, self.download_btn_EVT)

    def menu_EVT(self, event):
        evt_id = event.GetId()

        # 检查更新
        if evt_id == 100:
            wx.CallAfter(self.check_update)

        # 更新日志
        elif evt_id == 110:
            self.dlgbox(open(os.path.join(os.getcwd(), "CHANGELOG"), "r", encoding = "utf-8").read(), "更新日志", wx.ICON_INFORMATION)

        # 关于
        elif evt_id == 130:
            AboutWindow(self)

        # 用户中心
        elif evt_id == 200:
            # 判断是否登录
            if Config.user_name == "":
                LoginWindow(self).ShowWindowModal()
            else:
                UserWindow(self).ShowWindowModal()

        # 设置
        elif evt_id == 210:
            SettingWindow(self).ShowWindowModal()

        # 调试
        elif evt_id == 220:
            DebugWindow(self).Show()
            
    def get_btn_EVT(self, event):
        # 识别链接
        url = self.url_box.GetValue()

        if url == "": return

        self.reset()

        self.processing_window = ProcessingWindow(self)

        # 开启线程
        Thread(target = self.get_thread, args = (url,)).start()

        self.processing_window.ShowWindowModal()

    def get_thread(self, url: str):
        wx.CallAfter(self.treelist.init_list)

        # 短链接
        if find_str("b23.tv", url):
            url = process_shortlink(url)
        
        # if "live" in url:
        #     self.theme = LiveInfo
        #     live_parser.parse_url(url)

        #     self.set_live_list()

        # elif "audio" in url:
        #     self.theme = AudioInfo
        #     audio_parser.parse_url(url)

        #     self.set_audio_list()
        # 视频链接
        if find_str("BV|av", url):
            self.type = VideoInfo
            self.video_parser.parse_url(url)

            self.set_video_list()
            self.set_quality(VideoInfo)

        # 番组链接
        elif find_str("ep|ss|md", url):
            self.type = BangumiInfo
            self.bangumi_parser.parse_url(url)

            self.set_bangumi_list()
            self.set_quality(BangumiInfo)

        # 无法识别的链接，抛出异常
        else:
            self.onError(400)

        wx.CallAfter(self.get_finished)

    def reset(self):
        # 重置相关变量和控件
        self.quality_choice.Clear()
        self.type_lab.SetLabel("视频")
        self.download_btn.Enable(False)

        VideoInfo.down_pages.clear()
        BangumiInfo.down_episodes.clear()

    def get_finished(self):
        # 解析链接完成
        # if self.theme == LiveInfo:
        #     self.quality_cb.Enable(False)
        #     self.download_btn.SetLabel("播放")

        # elif self.theme == AudioInfo:
        #     self.quality_choice.Enable(False)
        #     self.download_btn.SetLabel("下载音频")

        # else:
        #     self.quality_choice.Enable(True)
        #     self.download_btn.SetLabel("下载视频")

        self.download_btn.Enable(True)

        self.processing_window.Hide()

        self.treelist.SetFocus()

        if Config.user_sessdata == "" and self.type == BangumiInfo:
            self.infobar.ShowMessageInfo(200)

    def set_video_list(self):
        # 显示视频列表
        videos = len(VideoInfo.episodes) if VideoInfo.collection else len(VideoInfo.pages)

        wx.CallAfter(self.treelist.set_video_list)
        self.type_lab.SetLabel("视频 (共 %d 个)" % videos)

    def set_bangumi_list(self):
        # 显示番组列表
        bangumis = len(BangumiInfo.episodes)

        wx.CallAfter(self.treelist.set_bangumi_list)
        self.type_lab.SetLabel("{} (正片共 {} 集)".format(BangumiInfo.type, bangumis))

    def set_quality(self, type):
        # 显示清晰度列表
        self.quality_choice.Set(type.quality_desc)
        
        # 选择默认清晰度
        type.quality = Config.default_quality if Config.default_quality in type.quality_id else type.quality_id[0]
        self.quality_choice.Select(type.quality_id.index(type.quality))
    
    def download_btn_EVT(self, event):
        if not self.treelist.get_allcheckeditem(self.type): return

        self.download_mgr_btn_EVT(0)

        self.download_window.add_download_task(self.type, quality_wrap[self.quality_choice.GetStringSelection()])

    def download_mgr_btn_EVT(self, event):
        # 下载管理按钮事件
        if self.show_download_window:
            # 如果下载管理窗口已经打开，则切换到该窗口
            self.download_window.Show()

        else:
            # 初始化下载管理窗口
            self.download_window = DownloadWindow(self)
            self.download_window.Show()

            # 设置下载管理窗口打开状态
            self.show_download_window = True

    def userinfo_EVT(self, event):
        # 用户信息事件
        # 判断登录状态
        if Config.user_name != "":
            UserWindow(self).ShowWindowModal()
        else:
            LoginWindow(self).ShowWindowModal()

    def check_update(self):
        # 检查更新
        json = check_update()

        # 如果有新版本，则弹出对话框
        if int(json["version_code"]) > Config.app_version_code:
            dlg = wx.MessageDialog(self, "有新的更新可用\n\nVersion {} 已于 {} 发布，详细更新日志请访问项目主页".format(json["version"], json["date"]), "检查更新", wx.ICON_INFORMATION | wx.YES_NO)
            dlg.SetYesNoLabels("查看", "忽略")

            # 打开浏览器，进入 release 页面
            if dlg.ShowModal() == wx.ID_YES:
                import webbrowser

                webbrowser.open(json["url"])
            
        else:
            self.dlgbox("当前没有可用的更新", "检查更新", wx.ICON_INFORMATION)
    
    def check_ffmpeg(self):
        if not Config.ffmpeg_available:
            dlg = wx.MessageDialog(self, "未安装 ffmpeg\n\n检测到您尚未安装 ffmpeg，无法正常合成视频，是否现在安装？", "提示", wx.ICON_INFORMATION | wx.YES_NO)

            if dlg.ShowModal() == wx.ID_YES:
                import webbrowser

                webbrowser.open("https://scott.o5g.top/index.php/archives/120/")

    def check_login(self):
        import locale

        #locale.setlocale(locale.LC_ALL, "English_United-Status")
        expire = expire = datetime.datetime.strptime(Config.user_expire, "%Y-%m-%d %H:%M:%S")
        
        if expire == "":
            return

        now = datetime.datetime.now()

        if (expire - now).days <= 0:
            wx.MessageDialog(self, "登录过期\n\n登录状态过期，请重新扫码登录。", "提示", wx.ICON_INFORMATION).ShowModal()

    def onSetFoucus(self, event):
        # 地址栏得到焦点事件
        if self.url_box.GetValue() == "请输入 URL 链接":
            self.url_box.Clear()
            self.url_box.SetForegroundColour("black")

        event.Skip()
    
    def onKillFocus(self, event):
        # 地址栏失去焦点事件
        if self.url_box.GetValue() == "":
            self.url_box.SetValue("请输入 URL 链接")
            self.url_box.SetForegroundColour(wx.Colour(117, 117, 117))
        
        event.Skip()

    def onError(self, code: int):
        # 抛出异常回调函数
        wx.CallAfter(self.processing_window.Hide)

        self.infobar.ShowMessageInfo(code)

    def onRedirect(self, url: str):
        # 检测到番组时重定向
        Thread(target = self.get_thread, args = (url,)).start()
        