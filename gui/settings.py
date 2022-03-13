import wx
import os
import configparser

from gui.template import Dialog, InfoBar

from utils.config import Config
from utils.tools import quality_wrap

conf = configparser.RawConfigParser()
conf.read(os.path.join(os.getcwd(), "config.conf"))

class SettingWindow(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent, "设置", (370, 450))

        self.init_controls()
        self.Bind_EVT()

    def init_controls(self):
        self.infobar = InfoBar(self.panel)

        self.note = wx.Notebook(self.panel, -1)

        tab1 = Tab1(self.note)
        tab2 = Tab2(self.note)
        tab3 = Tab3(self.note)
        #tab4 = Tab4(self.note)

        self.note.AddPage(tab1, "下载")
        self.note.AddPage(tab2, "Cookie")
        self.note.AddPage(tab3, "其他")
        #self.note.AddPage(tab4, "代理")

        self.ok_btn = wx.Button(self.panel, -1, "确定", size = self.FromDIP((80, 30)))
        self.cancel_btn = wx.Button(self.panel, -1, "取消", size = self.FromDIP((80, 30)))

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.AddStretchSpacer(1)
        hbox.Add(self.ok_btn, 0, wx.ALL & (~wx.TOP), 10)
        hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.TOP), 10)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.infobar)
        vbox.Add(self.note, 1, wx.EXPAND | wx.ALL, 10)
        vbox.Add(hbox, 0, wx.EXPAND)

        self.panel.SetSizer(vbox)
    
    def Bind_EVT(self):
        self.cancel_btn.Bind(wx.EVT_BUTTON, self.close_dialog)
        self.ok_btn.Bind(wx.EVT_BUTTON, self.save_settings)
    
    def close_dialog(self, event):
        self.Destroy()
    
    def save_settings(self, event):
        page = self.note.GetCurrentPage()
        page.save_conf()

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

        self.thread_sl.Bind(wx.EVT_SLIDER, self.on_slide)

    def load_conf(self):
        self.path_tc.SetLabel(Config.download_path)
        
        self.thread_lb.SetLabel("多线程数：{}".format(Config.max_thread))
        self.thread_sl.SetValue(Config.max_thread)
        self.quality_cb.Select(list(quality_wrap.values()).index(Config.default_quality))
        self.show_toast_chk.SetValue(Config.show_notification)

    def save_conf(self):
        Config.download_path = self.path_tc.GetValue()
        Config.max_thread = self.thread_sl.GetValue()
        Config.default_quality = list(quality_wrap.values())[self.quality_cb.GetSelection()]
        Config.show_notification = self.show_toast_chk.GetValue()

        conf.set("download", "path", Config.download_path if Config.download_path != Config.default_path else "default")
        conf.set("download", "max_thread", str(Config.max_thread))
        conf.set("download", "default_quality", str(Config.default_quality))
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
        self.thread_sl = wx.Slider(download_box, -1, 0, 1, 12)
        self.thread_sl.SetToolTip("设置下载视频的多线程数，范围 1-12\n\n下载速度最终取决于B站服务器的速度，设置太高可能会没有效果")

        quality_lb = wx.StaticText(download_box, -1, "默认下载清晰度")
        self.quality_cb = wx.Choice(download_box, -1, choices = list(quality_wrap.keys()))
        self.quality_cb.SetToolTip("设置默认下载的清晰度，如果视频没有所选的清晰度，则自动选择可用的最高清晰度")

        self.show_toast_chk = wx.CheckBox(download_box, -1, "下载完成后显示通知")
        self.show_toast_chk.SetToolTip("下载完成后显示通知，而不是对话框")

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(path_lb, 0, wx.ALL, 10)
        vbox.Add(hbox, 0, wx.EXPAND)
        vbox.Add(self.thread_lb, 0, wx.ALL & (~wx.TOP), 10)
        vbox.Add(self.thread_sl, 0, wx.EXPAND | wx.ALL & (~wx.TOP), 10)
        vbox.Add(quality_lb, 0, wx.ALL & (~wx.TOP), 10)
        vbox.Add(self.quality_cb, 0, wx.ALL & (~wx.TOP), 10)
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

    def on_slide(self, event):
        self.thread_lb.SetLabel("多线程数：{}".format(self.thread_sl.GetValue()))

class Tab2(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        self.vbox = wx.BoxSizer(wx.VERTICAL)

        self.Set_Cookie()

        self.SetSizer(self.vbox)

        self.load_conf()

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
        desp = wx.StaticText(cookie_box, -1, "说明：Cookie 用于下载大会员相关的视频\n\n添加方法：浏览器登录B站，按下 F12 键打开开发者工具，选择 应用(application) 选项卡 -> cookie，找到 SESSDATA 字段，复制粘贴即可。\n\n注：Cookie 有效期为一个月，请定期更换。")

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(sessdata_lb, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        hbox.Add(self.sessdata_tc, 1, wx.ALL & (~wx.LEFT), 10)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(hbox, 0, wx.EXPAND)
        vbox.Add(desp, 1, wx.ALL, 10)

        cookie_sbox = wx.StaticBoxSizer(cookie_box)
        cookie_sbox.Add(vbox, 1, wx.EXPAND)
        
        self.vbox.Add(cookie_sbox, 1, wx.ALL | wx.EXPAND, 10)

class Tab3(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        self.vbox = wx.BoxSizer(wx.VERTICAL)

        self.Set_Display()
        self.Set_danmaku()
        self.Set_Update()

        self.SetSizer(self.vbox)

        self.load_conf()

    def load_conf(self):
        self.show_sections_chk.SetValue(Config.show_sections)
        self.save_danmaku_chk.SetValue(Config.save_danmaku)
        self.auto_check_chk.SetValue(Config.auto_check_update)

    def save_conf(self):
        Config.show_sections = self.show_sections_chk.GetValue()
        Config.save_danmaku = self.save_danmaku_chk.GetValue()
        Config.auto_check_update = self.auto_check_chk.GetValue()

        conf.set("options", "show_sections", str(int(Config.show_sections)))
        conf.set("options", "save_danmaku", str(int(Config.save_danmaku)))
        conf.set("options", "auto_check_update", str(int(Config.auto_check_update)))
        
    def Set_Display(self):
        display_box = wx.StaticBox(self, -1, "剧集列表显示设置")

        self.show_sections_chk = wx.CheckBox(display_box, -1, "显示完整剧集列表 (包括PV、特别企划等)")

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.show_sections_chk, 0, wx.ALL, 10)
        
        display_sbox = wx.StaticBoxSizer(display_box)
        display_sbox.Add(vbox, 1, wx.EXPAND)

        self.vbox.Add(display_sbox, 0, wx.ALL | wx.EXPAND, 10)
    
    def Set_danmaku(self):
        danmaku_box = wx.StaticBox(self, -1, "弹幕下载设置")

        self.save_danmaku_chk = wx.CheckBox(danmaku_box, -1, "下载弹幕文件")
        danmaku_type_lb = wx.StaticText(danmaku_box, -1, "弹幕文件格式")
        danmaku_type_cb = wx.ComboBox(danmaku_box, -1, choices = ["xml"], style = wx.CB_READONLY)
        danmaku_type_cb.SetSelection(0)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(danmaku_type_lb, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, 10)
        hbox.Add(danmaku_type_cb, 0, wx.ALL & (~wx.TOP), 10)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.save_danmaku_chk, 0, wx.ALL, 10)
        vbox.Add(hbox)

        danmaku_sbox = wx.StaticBoxSizer(danmaku_box)
        danmaku_sbox.Add(vbox)

        self.vbox.Add(danmaku_sbox, 0, wx.ALL | wx.EXPAND, 10)

    def Set_Update(self):
        update_box = wx.StaticBox(self, -1, "检查更新设置")

        self.auto_check_chk = wx.CheckBox(update_box, -1, "自动检查更新")

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.auto_check_chk, 0, wx.ALL, 10)
        
        update_sbox = wx.StaticBoxSizer(update_box)
        update_sbox.Add(vbox, 1, wx.EXPAND)

        self.vbox.Add(update_sbox, 0, wx.ALL | wx.EXPAND, 10)

class Tab4(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        self.vbox = wx.BoxSizer(wx.VERTICAL)

        self.Set_Cookie()

        self.SetSizer(self.vbox)

    def load_conf(self):
        self.addresss_tc.SetValue()
        
    def Set_Cookie(self):
        proxy_box = wx.StaticBox(self, -1, "代理设置")

        address_lb = wx.StaticText(proxy_box, -1, "地址")
        self.addresss_tc = wx.TextCtrl(proxy_box, -1)

        port_lb = wx.StaticText(proxy_box, -1, "端口")
        self.port_tc = wx.TextCtrl(proxy_box, -1)

        hbox1 = wx.BoxSizer(wx.HORIZONTAL)
        hbox1.Add(address_lb, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        hbox1.Add(self.addresss_tc, 1, wx.EXPAND | wx.ALL & (~wx.LEFT), 10)

        hbox2 = wx.BoxSizer(wx.HORIZONTAL)
        hbox2.Add(port_lb, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        hbox2.Add(self.port_tc, 1, wx.EXPAND | wx.ALL & (~wx.LEFT), 10)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(hbox1, 1, wx.EXPAND)
        vbox.Add(hbox2, 1, wx.EXPAND)

        cookie_sbox = wx.StaticBoxSizer(proxy_box)
        cookie_sbox.Add(vbox)

        self.vbox.Add(cookie_sbox, 0, wx.ALL | wx.EXPAND, 10)