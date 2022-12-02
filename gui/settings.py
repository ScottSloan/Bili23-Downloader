import wx
import os
import time
import requests
from threading import Thread
from requests.auth import HTTPProxyAuth
from configparser import RawConfigParser

from .templates import Dialog

from utils.config import Config
from utils.tools import *

class SettingWindow(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent, "设置", (400, 500))

        self.init_UI()
        self.Bind_EVT()

        self.CenterOnParent()

    def init_UI(self):
        self.note = wx.Notebook(self.panel, -1)

        self.note.AddPage(DownloadTab(self.note), "下载")
        self.note.AddPage(SaveTab(self.note), "弹幕&&字幕&&歌词")
        self.note.AddPage(ProxyTab(self.note), "代理")
        self.note.AddPage(MiscTab(self.note), "其他")

        botton_hbox = wx.BoxSizer(wx.HORIZONTAL)

        self.ok_btn = wx.Button(self.panel, -1, "确定", size = self.FromDIP((80, 30)))
        self.cancel_btn = wx.Button(self.panel, -1, "取消", size = self.FromDIP((80, 30)))

        botton_hbox.AddStretchSpacer(1)
        botton_hbox.Add(self.ok_btn, 0, wx.ALL & (~wx.TOP), 10)
        botton_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), 10)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.note, 1, wx.EXPAND | wx.ALL, 10)
        vbox.Add(botton_hbox, 0, wx.EXPAND)

        self.panel.SetSizer(vbox)

        vbox.Fit(self)
    
    def Bind_EVT(self):
        self.cancel_btn.Bind(wx.EVT_BUTTON, self.cancel_btn_EVT)
        self.ok_btn.Bind(wx.EVT_BUTTON, self.ok_btn_EVT)
    
    def cancel_btn_EVT(self, event):
        self.Destroy()
    
    def ok_btn_EVT(self, event):
        for i in range(4):
            if self.note.GetPage(i).save_conf():
                return

        with open(os.path.join(os.getcwd(), "config.conf"), "w", encoding = "utf-8") as f:
            conf.write(f)

        self.Destroy()

class DownloadTab(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        self.vbox = wx.BoxSizer(wx.VERTICAL)
        
        self.init_UI()

        self.SetSizer(self.vbox)

        self.Bind_EVT()
        self.load_conf()

    def Bind_EVT(self):
        self.path_box.Bind(wx.EVT_TEXT, self.onChangePath)
        self.browse_btn.Bind(wx.EVT_BUTTON, self.browse_btn_EVT)

        self.thread_slider.Bind(wx.EVT_SLIDER, self.onThreadSlide)

        self.mode_choice.Bind(wx.EVT_CHOICE, self.onChangeMode)

    def load_conf(self):
        self.onChangeMode(0)

        self.path_box.SetValue(Config.download_path if Config.download_path != "" else os.path.join(os.getcwd(), "download"))
        
        self.thread_lab.SetLabel("多线程数：{}".format(Config.max_thread))
        self.thread_slider.SetValue(Config.max_thread)
        
        self.mode_choice.SetSelection(mode_wrap[Config.mode])
        self.quality_choice.SetSelection(list(quality_wrap.values()).index(Config.default_quality))
        self.codec_choice.SetSelection(codec_wrap[Config.codec])
        self.show_toast_chk.SetValue(Config.show_notification)

    def save_conf(self):
        if self.codec_choice.GetSelection() == wx.NOT_FOUND:
            wx.MessageDialog(self, "操作无效\n\n未选择视频编码", "错误", wx.ICON_WARNING).ShowModal()
            return True

        mode_dict = dict(map(reversed, mode_wrap.items()))
        codec_dict = dict(map(reversed, codec_wrap.items()))

        Config.download_path = self.path_box.GetValue()
        Config.max_thread = self.thread_slider.GetValue()
        Config.mode = mode_dict[self.mode_choice.GetSelection()]
        Config.default_quality = list(quality_wrap.values())[self.quality_choice.GetSelection()]
        Config.codec = codec_dict[self.codec_choice.GetSelection()]
        Config.show_notification = self.show_toast_chk.GetValue()

        conf.set("download", "path", Config.download_path)
        conf.set("download", "thread", str(Config.max_thread))
        conf.set("download", "mode", str(Config.mode))
        conf.set("download", "quality", str(Config.default_quality))
        conf.set("download", "codec", str(Config.codec))
        conf.set("download", "notification", str(int(Config.show_notification)))

    def init_UI(self):
        self.download_box = wx.StaticBox(self, -1, "下载设置")

        path_hbox = wx.BoxSizer(wx.HORIZONTAL)

        path_lab = wx.StaticText(self.download_box, -1, "下载目录")
        self.path_box = wx.TextCtrl(self.download_box, -1, size = self.FromDIP((200, 24)))
        self.browse_btn = wx.Button(self.download_box, -1, "选择目录", size = self.FromDIP((70, 24)))
        self.browse_btn.SetToolTip("选择下载目录")

        path_hbox.Add(self.path_box, 1, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, 10)
        path_hbox.Add(self.browse_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), 10)
        
        self.thread_lab = wx.StaticText(self.download_box, -1, "多线程数：0")
        self.thread_slider = wx.Slider(self.download_box, -1, 1, 1, 16)
        self.thread_slider.SetToolTip("设置下载视频的多线程数，范围 1-16")

        mode_hbox = wx.BoxSizer(wx.HORIZONTAL)

        mode_lab = wx.StaticText(self.download_box, -1, "视频解析方式")
        self.mode_choice = wx.Choice(self.download_box, -1, choices = ["API 接口", "网页"])
        self.mode_choice.SetToolTip("设置视频解析方式")
        self.mode_tip = wx.StaticText(self.download_box, -1, "说明")

        mode_hbox.Add(mode_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, 10)
        mode_hbox.Add(self.mode_choice, 0, wx.ALL & (~wx.TOP), 10)

        quality_hbox = wx.BoxSizer(wx.HORIZONTAL)

        lab = wx.StaticText(self.download_box, -1, "默认下载清晰度")
        self.quality_choice = wx.Choice(self.download_box, -1, choices = list(quality_wrap.keys()))
        self.quality_choice.SetToolTip("设置默认下载的清晰度\n如果视频没有所选的清晰度，则自动选择可用的最高清晰度")

        quality_hbox.Add(lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        quality_hbox.Add(self.quality_choice, 0, wx.ALL, 10)

        codec_lab = wx.StaticText(self.download_box, -1, "视频编码格式   ")
        self.codec_choice = wx.Choice(self.download_box, -1, choices = ["AVC/H.264", "HEVC/H.265", "AV1"])
        self.codec_choice.SetToolTip("设置默认下载的视频编码格式\n注意 HEVC/H.265 和 AV1 编码需设备支持才能正常播放")

        codec_hbox = wx.BoxSizer(wx.HORIZONTAL)
        codec_hbox.Add(codec_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        codec_hbox.Add(self.codec_choice, 0, wx.ALL, 10)

        self.show_toast_chk = wx.CheckBox(self.download_box, -1, "下载完成后弹出通知")
        self.show_toast_chk.SetToolTip("下载完成后弹出 Toast 通知")

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(path_lab, 0, wx.ALL, 10)
        vbox.Add(path_hbox, 0, wx.EXPAND)
        vbox.Add(self.thread_lab, 0, wx.ALL & (~wx.TOP), 10)
        vbox.Add(self.thread_slider, 0, wx.EXPAND | wx.ALL & (~wx.TOP), 10)
        vbox.Add(mode_hbox)
        vbox.Add(self.mode_tip, 0, wx.ALL & (~wx.TOP), 10)
        vbox.AddSpacer(self.FromDIP(10))
        vbox.Add(quality_hbox)
        vbox.Add(codec_hbox)
        vbox.Add(self.show_toast_chk, 0, wx.ALL, 10)

        download_sbox = wx.StaticBoxSizer(self.download_box)
        download_sbox.Add(vbox, 1, wx.EXPAND)

        self.vbox.Add(download_sbox, 0, wx.ALL | wx.EXPAND, 10)

    def browse_btn_EVT(self, event):
        dlg = wx.DirDialog(self, "选择下载目录", defaultPath = Config.download_path)

        if dlg.ShowModal() == wx.ID_OK:
            save_path = dlg.GetPath()
            self.path_box.SetValue(save_path)

        dlg.Destroy()

    def onChangePath(self, event):
        self.path_box.SetToolTip(self.path_box.GetValue())

    def onThreadSlide(self, event):
        self.thread_lab.SetLabel("多线程数：{}".format(self.thread_slider.GetValue()))

    def onChangeMode(self, event):
        if self.mode_choice.GetSelection() == 0:
            self.mode_tip.SetLabel("说明：API 接口方式解析需登录才能正常使用\n否则只能下载 480P 视频")
        else:
            self.mode_tip.SetLabel("说明：网页方式解析可免登录下载部分 1080P 视频")

        self.mode_tip.Wrap(self.download_box.Size[0])

class SaveTab(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        self.vbox = wx.BoxSizer(wx.VERTICAL)

        self.init_danmaku_UI()
        self.init_subtitle_UI()
        self.init_lyric_UI()

        self.SetSizer(self.vbox)

        self.load_conf()

    def load_conf(self):
        self.save_danmaku_chk.SetValue(Config.save_danmaku)
        self.save_subtitle_chk.SetValue(Config.save_subtitle)
        self.save_lyric_chk.SetValue(Config.save_lyric)

    def save_conf(self):
        Config.save_danmaku = self.save_danmaku_chk.GetValue()

        Config.save_subtitle = self.save_subtitle_chk.GetValue()
        Config.save_lyric = self.save_lyric_chk.GetValue()

        conf.set("save", "danmaku", str(int(Config.save_danmaku)))
        conf.set("save", "subtitle", str(int(Config.save_subtitle)))
        conf.set("save", "lyric", str(int(Config.save_lyric)))

    def init_danmaku_UI(self):
        danmaku_box = wx.StaticBox(self, -1, "弹幕下载设置")

        self.save_danmaku_chk = wx.CheckBox(danmaku_box, -1, "下载弹幕文件")
        self.save_danmaku_chk.SetToolTip("下载弹幕文件，保存为 xml 格式")
        
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.save_danmaku_chk, 0, wx.ALL, 10)

        danmaku_sbox = wx.StaticBoxSizer(danmaku_box)
        danmaku_sbox.Add(vbox)

        self.vbox.Add(danmaku_sbox, 0, wx.ALL | wx.EXPAND, 10)

    def init_subtitle_UI(self):
        subtitle_box = wx.StaticBox(self, -1, "字幕下载设置")

        self.save_subtitle_chk = wx.CheckBox(subtitle_box, -1, "下载字幕文件")
        self.save_subtitle_chk.SetToolTip("下载字幕文件，保存为 srt 格式\n如果有多个将全部下载")

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.save_subtitle_chk, 0, wx.ALL, 10)

        subtitle_sbox = wx.StaticBoxSizer(subtitle_box)
        subtitle_sbox.Add(vbox)

        self.vbox.Add(subtitle_sbox, 0, wx.ALL | wx.EXPAND, 10)

    def init_lyric_UI(self):
        lyric_box = wx.StaticBox(self, -1, "歌词下载设置")

        self.save_lyric_chk = wx.CheckBox(lyric_box, -1, "下载歌词文件")
        self.save_lyric_chk.SetToolTip("下载歌词文件，保存为 lrc 格式")

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.save_lyric_chk, 0, wx.ALL, 10)

        lyric_sbox = wx.StaticBoxSizer(lyric_box)
        lyric_sbox.Add(vbox)

        self.vbox.Add(lyric_sbox, 0, wx.ALL | wx.EXPAND, 10)

class MiscTab(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        self.vbox = wx.BoxSizer(wx.VERTICAL)

        self.init_sections_UI()
        self.init_player_UI()
        self.init_misc_UI()

        self.SetSizer(self.vbox)
        self.Bind_EVT()

        self.load_conf()

    def Bind_EVT(self):
        self.path_box.Bind(wx.EVT_TEXT, self.onChangePath)
        self.browse_btn.Bind(wx.EVT_BUTTON, self.browse_btn_EVT)

    def load_conf(self):
        self.show_sections_chk.SetValue(Config.show_sections)
        self.path_box.SetValue(Config.player_path)
        self.check_update_chk.SetValue(Config.check_update)
        self.debug_chk.SetValue(Config.debug)

    def save_conf(self):
        Config.show_sections = self.show_sections_chk.GetValue()
        Config.player_path = self.path_box.GetValue()
        Config.check_update = self.check_update_chk.GetValue()
        Config.debug = self.debug_chk.GetValue()

        conf.set("misc", "sections", str(int(Config.show_sections)))
        conf.set("misc", "player_path", Config.player_path)
        conf.set("misc", "update", str(int(Config.check_update)))
        conf.set("misc", "debug", str(int(Config.debug)))
    
    def init_sections_UI(self):
        sections_box = wx.StaticBox(self, -1, "剧集列表显示设置")

        self.show_sections_chk = wx.CheckBox(sections_box, -1, "显示非正片剧集 (如花絮、PV、OP、ED 等)")

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.show_sections_chk, 0, wx.ALL, 10)
        
        sections_sbox = wx.StaticBoxSizer(sections_box)
        sections_sbox.Add(vbox, 1, wx.EXPAND)

        self.vbox.Add(sections_sbox, 0, wx.ALL | wx.EXPAND, 10)

    def init_player_UI(self):
        player_box = wx.StaticBox(self, -1, "播放器设置")

        path_lab = wx.StaticText(player_box, -1, "播放器路径")
        self.path_box = wx.TextCtrl(player_box, -1)
        self.browse_btn = wx.Button(player_box, -1, "选择路径")
        self.browse_btn.SetToolTip("选择播放器路径")

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.path_box, 1, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, 10)
        hbox.Add(self.browse_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), 10)
        
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(path_lab, 0, wx.ALL, 10)
        vbox.Add(hbox, 1, wx.EXPAND)

        player_sbox = wx.StaticBoxSizer(player_box)
        player_sbox.Add(vbox, 1, wx.EXPAND)

        self.vbox.Add(player_sbox, 0, wx.ALL | wx.EXPAND, 10)

    def init_misc_UI(self):
        misc_box = wx.StaticBox(self, -1, "杂项")

        self.check_update_chk = wx.CheckBox(misc_box, -1, "自动检查更新")
        self.check_update_chk.SetToolTip("在程序启动时检查更新")

        self.debug_chk = wx.CheckBox(misc_box, -1, "启用调试模式")
        self.debug_chk.SetToolTip("启用后，可在“工具”菜单项中找到调试入口")

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.check_update_chk, 0, wx.ALL & (~wx.TOP), 10)
        vbox.Add(self.debug_chk, 0, wx.ALL & ~(wx.TOP), 10)

        misc_sbox = wx.StaticBoxSizer(misc_box)
        misc_sbox.Add(vbox, 1, wx.EXPAND)

        self.vbox.Add(misc_sbox, 0, wx.ALL | wx.EXPAND, 10)

    def browse_btn_EVT(self, event):
        wildcard = "可执行文件(*.exe)|*.exe"
        dialog = wx.FileDialog(self, "选择播放器路径", os.getcwd(), wildcard = wildcard, style = wx.FD_OPEN)

        if dialog.ShowModal() == wx.ID_OK:
            self.path_box.SetValue(dialog.GetPath())

    def onChangePath(self, event):
        self.path_box.SetToolTip(self.path_box.GetValue())

class ProxyTab(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        self.vbox = wx.BoxSizer(wx.VERTICAL)

        self.init_proxy_UI()

        self.SetSizer(self.vbox)

        self.Bind_EVT()
        self.load_conf()
    
    def Bind_EVT(self):
        self.enable_chk.Bind(wx.EVT_CHECKBOX, self.enable_chk_EVT)
        self.auth_chk.Bind(wx.EVT_CHECKBOX, self.auth_chk_EVT)
        
        self.test_btn.Bind(wx.EVT_BUTTON, self.test_btn_EVT)

    def load_conf(self):
        if not Config.enable_proxy:
            self.set_proxy_enable(False)

        if not Config.enable_auth:
            self.set_auth_enable(False)

        self.enable_chk.SetValue(Config.enable_proxy)
        self.ip_box.SetValue(Config.proxy_ip)
        self.port_box.SetValue(Config.proxy_port)
    
        self.auth_chk.SetValue(Config.enable_proxy)
        self.uname_box.SetValue(Config.proxy_ip)
        self.pwd_box.SetValue(Config.proxy_port)

    def save_conf(self):
        Config.enable_proxy = self.enable_chk.GetValue()
        Config.proxy_ip = self.ip_box.GetValue()
        Config.proxy_port = self.port_box.GetValue()

        Config.enable_auth = self.enable_chk.GetValue()
        Config.auth_uname = self.ip_box.GetValue()
        Config.auth_pwd = self.port_box.GetValue()

        conf.set("proxy", "enable", str(int(Config.enable_proxy)))
        conf.set("proxy", "address", Config.proxy_ip)
        conf.set("proxy", "port", Config.proxy_port)

        conf.set("auth", "auth", str(int(Config.enable_auth)))
        conf.set("auth", "uname", Config.auth_uname)
        conf.set("auth", "pwd", Config.auth_pwd)

    def init_proxy_UI(self):
        proxy_box = wx.StaticBox(self, -1, "代理设置")
        
        self.enable_chk = wx.CheckBox(proxy_box, -1, "启用代理")
        
        ip_lab = wx.StaticText(proxy_box, -1, "地址")
        self.ip_box = wx.TextCtrl(proxy_box, -1)

        port_lab = wx.StaticText(proxy_box, -1, "端口")
        self.port_box = wx.TextCtrl(proxy_box, -1)

        self.auth_chk = wx.CheckBox(proxy_box, -1, "启用代理身份验证")
        
        uname_lab = wx.StaticText(proxy_box, -1, "用户名")
        self.uname_box = wx.TextCtrl(proxy_box, -1)

        pwd_lab = wx.StaticText(proxy_box, -1, "密码")
        self.pwd_box = wx.TextCtrl(proxy_box, -1)

        self.test_btn = wx.Button(proxy_box, -1, "测试", size = self.FromDIP((80, 30)))

        vbox = wx.BoxSizer(wx.VERTICAL)
        bag_box = wx.GridBagSizer(5, 4)

        bag_box.Add(ip_lab, pos = (0, 0), flag = wx.ALL | wx.ALIGN_CENTER, border = 10)
        bag_box.Add(self.ip_box, pos = (0, 1), span = (1, 3), flag = wx.ALL & (~wx.LEFT) | wx.EXPAND, border = 10)
        bag_box.Add(port_lab, pos = (1, 0), flag = wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, border = 10)
        bag_box.Add(self.port_box, pos = (1, 1), span = (1, 2), flag = wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.EXPAND, border = 10)

        bag_box.Add(self.auth_chk, pos = (2, 0), span = (1, 2), flag = wx.ALL | wx.EXPAND, border = 10)

        bag_box.Add(uname_lab, pos = (3, 0), flag = wx.ALL | wx.ALIGN_CENTER, border = 10)
        bag_box.Add(self.uname_box, pos = (3, 1), span = (1, 3), flag = wx.ALL & (~wx.LEFT) | wx.EXPAND, border = 10)
        bag_box.Add(pwd_lab, pos = (4, 0), flag = wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, border = 10)
        bag_box.Add(self.pwd_box, pos = (4, 1), span = (1, 3), flag = wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.EXPAND, border = 10)

        vbox.Add(self.enable_chk, 0, wx.ALL, 10)
        vbox.Add(bag_box)
        vbox.Add(self.test_btn, 0, wx.ALL, 10)

        proxy_sbox = wx.StaticBoxSizer(proxy_box)
        proxy_sbox.Add(vbox)

        self.vbox.Add(proxy_sbox, 0, wx.ALL | wx.EXPAND, 10)

    def set_proxy_enable(self, enable):
        self.ip_box.Enable(enable)
        self.port_box.Enable(enable)

    def set_auth_enable(self, enable):
        self.uname_box.Enable(enable)
        self.pwd_box.Enable(enable)

    def enable_chk_EVT(self, event):
        if event.IsChecked():
            self.set_proxy_enable(True)
        else:
            self.set_proxy_enable(False)

    def auth_chk_EVT(self, event):
        if event.IsChecked():
            self.set_auth_enable(True)
        else:
            self.set_auth_enable(False)
 
    def test_btn_EVT(self, event):
        if self.enable_chk.GetValue():
            proxy = {
                "http": "{}:{}".format(self.ip_box.GetValue(), self.port_box.GetValue()),
                "https": "{}:{}".format(self.ip_box.GetValue(), self.port_box.GetValue())
            }
        else:
            proxy = {}

        if self.auth_chk.GetValue():
            auth = HTTPProxyAuth(
                self.uname_box.GetValue(),
                self.pwd_box.GetValue()
            )
        else:
            auth = HTTPProxyAuth(None, None)

        Thread(target = self.test_website, args = (proxy, auth, )).start()

    def test_website(self, proxy, auth):
        try:
            start_time = time.time()

            req = requests.get(url = Config.app_bilibili_website, headers = get_header(), proxies = proxy, auth = auth, timeout = 3)
            
            end_time = time.time()

            wx.MessageDialog(self, "测试成功\n\n请求站点：{}\n状态码：{}\n耗时：{:.1f}s".format(Config.app_bilibili_website, req.status_code, end_time - start_time), "提示", wx.ICON_INFORMATION).ShowModal()

        except requests.RequestException as e:
            wx.MessageDialog(self, "测试失败\n\n请求站点：{}\n错误信息：\n\n{}".format(Config.app_bilibili_website, e), "测试代理", wx.ICON_WARNING).ShowModal()

conf = RawConfigParser()
conf.read(os.path.join(os.getcwd(), "config.conf"), encoding = "utf-8")