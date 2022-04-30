import wx
import os
import time
import requests
import configparser

from gui.templates import Dialog
from gui.login import LoginWindow

from utils.config import Config
from utils.tools import quality_wrap, get_header

conf = configparser.RawConfigParser()
conf.read(os.path.join(os.getcwd(), "config.conf"))

class SettingWindow(Dialog):
    def __init__(self, parent):
        self.parent = parent
        Dialog.__init__(self, parent, "设置", (400, 500))

        self.init_controls()
        self.Bind_EVT()

        self.FitInside()

    def init_controls(self):
        self.note = wx.Notebook(self.panel, -1)

        tab1 = Tab1(self.note)
        tab2 = Tab2(self.note, self.parent)
        tab3 = Tab3(self.note)
        tab4 = Tab4(self.note)
        tab5 = Tab5(self.note)

        self.note.AddPage(tab1, "下载")
        self.note.AddPage(tab2, "Cookie")
        self.note.AddPage(tab3, "弹幕&&字幕&&歌词")
        self.note.AddPage(tab4, "其他")
        self.note.AddPage(tab5, "代理")

        self.ok_btn = wx.Button(self.panel, -1, "确定", size = self.FromDIP((80, 30)))
        self.cancel_btn = wx.Button(self.panel, -1, "取消", size = self.FromDIP((80, 30)))

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.AddStretchSpacer(1)
        hbox.Add(self.ok_btn, 0, wx.ALL & (~wx.TOP), 10)
        hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.TOP), 10)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.note, 1, wx.EXPAND | wx.ALL, 10)
        vbox.Add(hbox, 0, wx.EXPAND)

        self.panel.SetSizer(vbox)
    
    def Bind_EVT(self):
        self.cancel_btn.Bind(wx.EVT_BUTTON, self.close_dialog)
        self.ok_btn.Bind(wx.EVT_BUTTON, self.save_settings)
    
    def close_dialog(self, event):
        self.Destroy()
    
    def save_settings(self, event):
        for i in range(5):
            self.note.GetPage(i).save_conf()

        with open(os.path.join(os.getcwd(), "config.conf"), "w", encoding = "utf-8") as f:
            conf.write(f)

        self.Destroy()

class Tab1(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        self.vbox = wx.BoxSizer(wx.VERTICAL)
        
        self.Set_Download()

        self.SetSizer(self.vbox)

        self.Bind_EVT()
        self.load_conf()

    def Bind_EVT(self):
        self.browse_btn.Bind(wx.EVT_BUTTON, self.browse_folder)

        self.thread_sl.Bind(wx.EVT_SLIDER, self.on_thread_slide)
        self.task_sl.Bind(wx.EVT_SLIDER, self.on_task_slide)

    def load_conf(self):
        self.path_tc.SetValue(Config.download_path)
        
        self.thread_lb.SetLabel("多线程数：{}".format(Config.max_thread))
        self.thread_sl.SetValue(Config.max_thread)
        self.task_lb.SetLabel("并行任务数：{}".format(Config.max_task))
        self.task_sl.SetValue(Config.max_task)
        self.quality_cb.SetSelection(list(quality_wrap.values()).index(Config.default_quality))
        self.codec_cb.SetSelection(Config.codec)
        self.show_toast_chk.SetValue(Config.show_notification)

    def save_conf(self):
        Config.download_path = self.path_tc.GetValue()
        Config.max_thread = self.thread_sl.GetValue()
        Config.max_task = self.task_sl.GetValue()
        Config.default_quality = list(quality_wrap.values())[self.quality_cb.GetSelection()]
        Config.codec = self.codec_cb.GetSelection()
        Config.show_notification = self.show_toast_chk.GetValue()

        conf.set("download", "path", Config.download_path if Config.download_path != Config.default_path else "default")
        conf.set("download", "max_thread", str(Config.max_thread))
        conf.set("download", "max_task", str(Config.max_task))
        conf.set("download", "default_quality", str(Config.default_quality))
        conf.set("download", "codec", str(Config.codec))
        conf.set("download", "show_notification", str(int(Config.show_notification)))

    def Set_Download(self):
        download_box = wx.StaticBox(self, -1, "下载设置")

        path_lb = wx.StaticText(download_box, -1, "下载目录")
        self.path_tc = wx.TextCtrl(download_box, -1)
        self.browse_btn = wx.Button(download_box, -1, "选择目录")
        self.browse_btn.SetToolTip("选择下载目录")

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.path_tc, 1, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, 10)
        hbox.Add(self.browse_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), 10)

        self.thread_lb = wx.StaticText(download_box, -1, "多线程数：0")
        self.thread_sl = wx.Slider(download_box, -1, 1, 1, 8)
        self.thread_sl.SetToolTip("设置下载视频的多线程数，范围 1-8")

        self.task_lb = wx.StaticText(download_box, -1, "并行任务数：0")
        self.task_sl = wx.Slider(download_box, -1, 1, 1, 5)
        self.task_sl.SetToolTip("设置并行下载视频的任务数，范围 1-5")

        quality_lb = wx.StaticText(download_box, -1, "默认下载清晰度")
        self.quality_cb = wx.Choice(download_box, -1, choices = list(quality_wrap.keys()))
        self.quality_cb.SetToolTip("设置默认下载的清晰度\n如果视频没有所选的清晰度，则自动选择可用的最高清晰度")

        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        hbox1.Add(quality_lb, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, 10)
        hbox1.Add(self.quality_cb, 0, wx.ALL & (~wx.TOP), 10)

        codec_lb = wx.StaticText(download_box, -1, "视频编码格式   ")
        self.codec_cb = wx.Choice(download_box, -1, choices = ["AVC/H.264", "HEVC/H.265", "AV1"])
        self.codec_cb.SetToolTip("设置默认下载的视频编码格式\n注意 HEVC/H.265 和 AV1 编码需设备支持才能正常播放")

        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        hbox2.Add(codec_lb, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        hbox2.Add(self.codec_cb, 0, wx.ALL, 10)

        self.show_toast_chk = wx.CheckBox(download_box, -1, "下载完成后弹出通知")
        self.show_toast_chk.SetToolTip("下载完成后弹出 Toast 通知")

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(path_lb, 0, wx.ALL, 10)
        vbox.Add(hbox, 0, wx.EXPAND)
        vbox.Add(self.thread_lb, 0, wx.ALL & (~wx.TOP), 10)
        vbox.Add(self.thread_sl, 0, wx.EXPAND | wx.ALL & (~wx.TOP), 10)
        vbox.Add(self.task_lb, 0, wx.ALL & (~wx.TOP), 10)
        vbox.Add(self.task_sl, 0, wx.EXPAND | wx.ALL & (~wx.TOP), 10)
        vbox.Add(hbox1)
        vbox.Add(hbox2)
        vbox.Add(self.show_toast_chk, 0, wx.ALL, 10)

        download_sbox = wx.StaticBoxSizer(download_box)
        download_sbox.Add(vbox, 1, wx.EXPAND)

        self.vbox.Add(download_sbox, 0, wx.ALL | wx.EXPAND, 10)

    def browse_folder(self, event):
        dlg = wx.DirDialog(self, "选择下载目录", defaultPath = Config.download_path)
        if dlg.ShowModal() == wx.ID_OK:
            save_path = dlg.GetPath()
            self.path_tc.SetLabel(save_path)
        dlg.Destroy()

    def on_thread_slide(self, event):
        self.thread_lb.SetLabel("多线程数：{}".format(self.thread_sl.GetValue()))

    def on_task_slide(self, event):
        self.task_lb.SetLabel("并行任务数：{}".format(self.task_sl.GetValue()))
 
class Tab2(wx.Panel):
    def __init__(self, parent, parent_w):
        self.parent = parent_w

        wx.Panel.__init__(self, parent, -1)

        self.vbox = wx.BoxSizer(wx.VERTICAL)

        self.Set_Cookie()

        self.SetSizer(self.vbox)

        self.Bind_EVT()

        self.load_conf()

    def Bind_EVT(self):
        self.login_btn.Bind(wx.EVT_BUTTON, self.Login_EVT)

    def load_conf(self):
        self.sessdata_tc.SetValue(Config.cookie_sessdata)

    def save_conf(self):
        Config.cookie_sessdata = self.sessdata_tc.GetValue()
        conf.set("cookie", "sessdata", Config.cookie_sessdata)

    def Set_Cookie(self):
        cookie_box = wx.StaticBox(self, -1, "Cookie 设置")

        sessdata_lb = wx.StaticText(cookie_box, -1, "SESSDATA")
        self.sessdata_tc = wx.TextCtrl(cookie_box, -1)
        self.sessdata_tc.SetToolTip("Cookie SESSDATA 字段")

        self.login_btn = wx.Button(cookie_box, -1, "扫码登录", size = self.FromDIP((90, 30)))

        desp = wx.StaticText(cookie_box, -1, """说明：Cookie 用于下载大会员相关的视频\n\n点击“扫码登录”按钮，可自动获取 Cookie 并填入\n\n注：Cookie 有效期为一个月，请定期更换""")

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(sessdata_lb, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        hbox.Add(self.sessdata_tc, 1, wx.ALL & (~wx.LEFT), 10)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(hbox, 0, wx.EXPAND)
        vbox.Add(self.login_btn, 0, wx.ALL & (~wx.TOP), 10)
        vbox.Add(desp, 1, wx.ALL, 10)

        cookie_sbox = wx.StaticBoxSizer(cookie_box)
        cookie_sbox.Add(vbox, 1, wx.EXPAND)
        
        self.vbox.Add(cookie_sbox, 1, wx.ALL | wx.EXPAND, 10)

    def Login_EVT(self, event):
        login_window = LoginWindow(self)
        login_window.ShowWindowModal()

class Tab3(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        self.vbox = wx.BoxSizer(wx.VERTICAL)

        self.Set_danmaku()
        self.Set_subtitle()
        self.Set_lyric()

        self.SetSizer(self.vbox)

        self.Bind_EVT()
        self.load_conf()

    def Bind_EVT(self):
        self.save_danmaku_chk.Bind(wx.EVT_CHECKBOX, self.save_danmaku_EVT)

    def load_conf(self):
        if not Config.save_danmaku:
            self.danmaku_format_cb.Enable(False)

        self.save_danmaku_chk.SetValue(Config.save_danmaku)
        self.danmaku_format_cb.SetSelection(Config.danmaku_format)

        self.save_subtitle_chk.SetValue(Config.save_subtitle)
        self.save_lyric_chk.SetValue(Config.save_lyric)

    def save_conf(self):
        Config.save_danmaku = self.save_danmaku_chk.GetValue()
        Config.danmaku_format = self.danmaku_format_cb.GetSelection()

        Config.save_subtitle = self.save_subtitle_chk.GetValue()
        Config.save_lyric = self.save_lyric_chk.GetValue()

        conf.set("danmaku", "save_danmaku", str(int(Config.save_danmaku)))
        conf.set("danmaku", "format", str(int(Config.danmaku_format)))

        conf.set("subtitle", "save_subtitle", str(int(Config.save_subtitle)))
        conf.set("lyric", "save_lyric", str(int(Config.save_lyric)))

    def Set_danmaku(self):
        danmaku_box = wx.StaticBox(self, -1, "弹幕下载设置")

        self.save_danmaku_chk = wx.CheckBox(danmaku_box, -1, "下载弹幕文件")
        self.save_danmaku_chk.SetToolTip("同时下载弹幕文件")
        danmaku_format_lb = wx.StaticText(danmaku_box, -1, "弹幕文件格式")
        self.danmaku_format_cb = wx.Choice(danmaku_box, -1, choices = ["xml", "ass", "proto"])
        self.danmaku_format_cb.SetToolTip("设置弹幕文件格式")

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(danmaku_format_lb, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, 10)
        hbox.Add(self.danmaku_format_cb, 0, wx.ALL & (~wx.TOP), 10)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.save_danmaku_chk, 0, wx.ALL, 10)
        vbox.Add(hbox)

        danmaku_sbox = wx.StaticBoxSizer(danmaku_box)
        danmaku_sbox.Add(vbox)

        self.vbox.Add(danmaku_sbox, 0, wx.ALL | wx.EXPAND, 10)

    def Set_subtitle(self):
        subtitle_box = wx.StaticBox(self, -1, "字幕下载设置")

        self.save_subtitle_chk = wx.CheckBox(subtitle_box, -1, "下载字幕文件")
        self.save_subtitle_chk.SetToolTip("下载字幕文件 (srt格式)\n如果有多个字幕将全部下载")

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.save_subtitle_chk, 0, wx.ALL, 10)

        subtitle_sbox = wx.StaticBoxSizer(subtitle_box)
        subtitle_sbox.Add(vbox)

        self.vbox.Add(subtitle_sbox, 0, wx.ALL | wx.EXPAND, 10)

    def Set_lyric(self):
        lyric_box = wx.StaticBox(self, -1, "歌词下载设置")

        self.save_lyric_chk = wx.CheckBox(lyric_box, -1, "下载歌词文件")
        self.save_lyric_chk.SetToolTip("下载歌词文件 (lrc格式)")

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.save_lyric_chk, 0, wx.ALL, 10)

        lyric_sbox = wx.StaticBoxSizer(lyric_box)
        lyric_sbox.Add(vbox)

        self.vbox.Add(lyric_sbox, 0, wx.ALL | wx.EXPAND, 10)

    def save_danmaku_EVT(self, event):
        state = event.IsChecked()

        if state:
            self.danmaku_format_cb.Enable(True)
        else:
            self.danmaku_format_cb.Enable(False)

class Tab4(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        self.vbox = wx.BoxSizer(wx.VERTICAL)

        self.Set_Display()
        self.Set_Player()
        self.Set_Misc()

        self.SetSizer(self.vbox)
        self.Bind_EVT()

        self.load_conf()

    def Bind_EVT(self):
        self.browse_btn.Bind(wx.EVT_BUTTON, self.browse_file)

    def load_conf(self):
        self.show_sections_chk.SetValue(Config.show_sections)
        self.path_tc.SetValue(Config.player_path)
        self.show_icon_chk.SetValue(Config.show_icon)
        self.auto_check_chk.SetValue(Config.auto_check_update)

    def save_conf(self):
        Config.show_sections = self.show_sections_chk.GetValue()
        Config.player_path = self.path_tc.GetValue()
        Config.show_icon = self.show_icon_chk.GetValue()
        Config.auto_check_update = self.auto_check_chk.GetValue()

        conf.set("other", "show_sections", str(int(Config.show_sections)))
        conf.set("other", "player_path", Config.player_path)
        conf.set("other", "show_icon", str(int(Config.show_icon)))
        conf.set("other", "auto_check_update", str(int(Config.auto_check_update)))
    
    def Set_Display(self):
        display_box = wx.StaticBox(self, -1, "剧集列表显示设置")

        self.show_sections_chk = wx.CheckBox(display_box, -1, "显示完整剧集列表 (包括PV、特别企划等)")

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.show_sections_chk, 0, wx.ALL, 10)
        
        display_sbox = wx.StaticBoxSizer(display_box)
        display_sbox.Add(vbox, 1, wx.EXPAND)

        self.vbox.Add(display_sbox, 0, wx.ALL | wx.EXPAND, 10)

    def Set_Player(self):
        player_box = wx.StaticBox(self, -1, "播放器设置")

        path_lb = wx.StaticText(player_box, -1, "播放器路径")
        self.path_tc = wx.TextCtrl(player_box, -1)
        self.browse_btn = wx.Button(player_box, -1, "选择路径")
        self.browse_btn.SetToolTip("选择播放器路径")

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.path_tc, 1, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, 10)
        hbox.Add(self.browse_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), 10)
        
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(path_lb, 0, wx.ALL, 10)
        vbox.Add(hbox, 1, wx.EXPAND)

        player_sbox = wx.StaticBoxSizer(player_box)
        player_sbox.Add(vbox, 1, wx.EXPAND)

        self.vbox.Add(player_sbox, 0, wx.ALL | wx.EXPAND, 10)

    def Set_Misc(self):
        misc_box = wx.StaticBox(self, -1, "杂项")

        self.show_icon_chk = wx.CheckBox(misc_box, -1, "显示托盘图标")
        self.auto_check_chk = wx.CheckBox(misc_box, -1, "自动检查更新")

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.show_icon_chk, 0, wx.ALL, 10)
        vbox.Add(self.auto_check_chk, 0, wx.ALL & (~wx.TOP), 10)
        
        misc_sbox = wx.StaticBoxSizer(misc_box)
        misc_sbox.Add(vbox, 1, wx.EXPAND)

        self.vbox.Add(misc_sbox, 0, wx.ALL | wx.EXPAND, 10)

    def browse_file(self, event):
        wildcard = "可执行文件(*.exe)|*.exe"
        dialog = wx.FileDialog(self, "选择播放器路径", os.getcwd(), wildcard = wildcard, style = wx.FD_OPEN)
        if dialog.ShowModal() == wx.ID_OK:
            self.path_tc.SetValue(dialog.GetPath())

class Tab5(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        self.vbox = wx.BoxSizer(wx.VERTICAL)

        self.Set_Proxy()

        self.SetSizer(self.vbox)

        self.Bind_EVT()
        self.load_conf()
    
    def Bind_EVT(self):
        self.enable_proxy_chk.Bind(wx.EVT_CHECKBOX, self.enable_chk_EVT)
        self.test_btn.Bind(wx.EVT_BUTTON, self.test_EVT)

    def load_conf(self):
        if not Config.enable_proxy:
            self.addresss_tc.Enable(False)
            self.port_tc.Enable(False)

        self.enable_proxy_chk.SetValue(Config.enable_proxy)
        self.addresss_tc.SetValue(Config.proxy_address)
        self.port_tc.SetValue(Config.proxy_port)
    
    def save_conf(self):
        Config.enable_proxy = self.enable_proxy_chk.GetValue()
        Config.proxy_address = self.addresss_tc.GetValue()
        Config.proxy_port = self.port_tc.GetValue()

        conf.set("proxy", "enable_proxy", str(int(Config.enable_proxy)))
        conf.set("proxy", "ip_address", Config.proxy_address)
        conf.set("proxy", "port", Config.proxy_port)

    def Set_Proxy(self):
        proxy_box = wx.StaticBox(self, -1, "代理设置")

        self.enable_proxy_chk =wx.CheckBox(proxy_box, -1, "启用代理")
        address_lb = wx.StaticText(proxy_box, -1, "地址")
        self.addresss_tc = wx.TextCtrl(proxy_box, -1)

        port_lb = wx.StaticText(proxy_box, -1, "端口")
        self.port_tc = wx.TextCtrl(proxy_box, -1)

        self.test_btn = wx.Button(proxy_box, -1, "测试", size = self.FromDIP((80, 30)))

        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        hbox1.Add(address_lb, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        hbox1.Add(self.addresss_tc, 1, wx.ALL & (~wx.LEFT), 10)

        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        hbox2.Add(port_lb, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, 10)
        hbox2.Add(self.port_tc, 1, wx.ALL & (~wx.LEFT) & (~wx.TOP), 10)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.enable_proxy_chk, 0, wx.ALL & (~wx.BOTTOM), 10)
        vbox.Add(hbox1)
        vbox.Add(hbox2)
        vbox.Add(self.test_btn, 0, wx.ALL & (~wx.TOP), 10)

        cookie_sbox = wx.StaticBoxSizer(proxy_box)
        cookie_sbox.Add(vbox)

        self.vbox.Add(cookie_sbox, 0, wx.ALL | wx.EXPAND, 10)

    def enable_chk_EVT(self, event):
        state = event.IsChecked()

        if state:
            self.addresss_tc.Enable(True)
            self.port_tc.Enable(True)
        else:
            self.addresss_tc.Enable(False)
            self.port_tc.Enable(False)
    
    def test_EVT(self, event):
        test_url = "https://www.bilibili.com"

        try:
            start_t = time.time()
            req = requests.get(test_url, get_header(), timeout = 3)
            end_t = time.time()

            wx.MessageDialog(self, "测试成功\n\n状态码：{}\n耗时：{:.1f}s".format(req.status_code, end_t - start_t), "提示", wx.ICON_INFORMATION).ShowModal()
        except:
            wx.MessageDialog(self, "测试失败\n\n状态码：{}".format(req.status_code), "提示", wx.ICON_WARNING).ShowModal()
