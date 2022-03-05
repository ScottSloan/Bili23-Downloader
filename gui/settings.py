import wx

from gui.template import Dialog
class SettingWindow(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent, "设置", (400, 500))

        self.init_controls()

    def init_controls(self):
        self.note = wx.Notebook(self.panel, -1)

        tab1 = Tab1(self.note)
        tab2 = Tab2(self.note)
        tab3 = Tab3(self.note)

        self.note.AddPage(tab1, "下载")
        self.note.AddPage(tab2, "Cookie")
        self.note.AddPage(tab3, "其他")
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.note, 1, wx.EXPAND | wx.ALL, 10)

        self.panel.SetSizer(vbox)

class Tab1(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        self.vbox = wx.BoxSizer(wx.VERTICAL)
        
        self.Set_Download()

        self.SetSizer(self.vbox)

    def Set_Download(self):
        download_box = wx.StaticBox(self, -1, "下载设置")

        path_lb = wx.StaticText(download_box, -1, "下载目录")
        path_tc = wx.TextCtrl(download_box, -1, style = wx.TE_READONLY)
        browse_btn = wx.Button(download_box, -1, "选择目录")

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(path_tc, 1, wx.EXPAND | wx.ALL & (~wx.TOP), 10)
        hbox.Add(browse_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), 10)

        thread_lb = wx.StaticText(download_box, -1, "多线程数 :  8")
        thread_sl = wx.Slider(download_box, -1, 8, 1, 16)

        show_toast_chk = wx.CheckBox(download_box, -1, "下载完成后显示通知")

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(path_lb, 0, wx.ALL, 10)
        vbox.Add(hbox, 0, wx.EXPAND)
        vbox.Add(thread_lb, 0, wx.ALL & (~wx.TOP), 10)
        vbox.Add(thread_sl, 0, wx.EXPAND | wx.ALL & (~wx.TOP), 10)
        vbox.Add(show_toast_chk, 0, wx.ALL & (~wx.TOP), 10)

        download_sbox = wx.StaticBoxSizer(download_box)
        download_sbox.Add(vbox, 1, wx.EXPAND)

        self.vbox.Add(download_sbox, 0, wx.ALL | wx.EXPAND, 10)

class Tab2(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        self.vbox = wx.BoxSizer(wx.VERTICAL)

        self.Set_Cookie()

        self.SetSizer(self.vbox)

    def Set_Cookie(self):
        cookie_box = wx.StaticBox(self, -1, "Cookie 设置")

        sessdata_lb = wx.StaticText(cookie_box, -1, "SESSDATA")
        self.sessdata_tc = wx.TextCtrl(cookie_box, -1)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(sessdata_lb, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        hbox.Add(self.sessdata_tc, 1, wx.EXPAND | wx.ALL & (~wx.LEFT), 10)

        cookie_sbox = wx.StaticBoxSizer(cookie_box)
        cookie_sbox.Add(hbox, 1, wx.EXPAND)

        self.vbox.Add(cookie_sbox, 0, wx.ALL | wx.EXPAND, 10)

class Tab3(wx.Panel):
    def __init__(self, parent):
        wx.Panel.__init__(self, parent, -1)

        self.vbox = wx.BoxSizer(wx.VERTICAL)

        self.Set_Display()
        self.Set_danmaku()

        self.SetSizer(self.vbox)
        
    def Set_Display(self):
        display_box = wx.StaticBox(self, -1, "番剧列表显示设置")

        show_pv_chk = wx.CheckBox(display_box, -1, "显示 PV&&其他 列表")
        show_sr_chk = wx.CheckBox(display_box, -1, "显示 特别企划 列表")
        show_hl_chk = wx.CheckBox(display_box, -1, "显示 高能亮点 列表")

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(show_pv_chk, 0, wx.ALL, 10)
        vbox.Add(show_sr_chk, 0, wx.ALL & (~wx.TOP), 10)
        vbox.Add(show_hl_chk, 0, wx.ALL & (~wx.TOP), 10)
        
        display_sbox = wx.StaticBoxSizer(display_box)
        display_sbox.Add(vbox, 1, wx.EXPAND)

        self.vbox.Add(display_sbox, 0, wx.ALL | wx.EXPAND, 10)
    
    def Set_danmaku(self):
        danmaku_box = wx.StaticBox(self, -1, "弹幕下载设置")

        down_danmaku_chk = wx.CheckBox(danmaku_box, -1, "下载弹幕文件")
        danmaku_type_lb = wx.StaticText(danmaku_box, -1, "弹幕文件格式")
        danmaku_type_cb = wx.ComboBox(danmaku_box, -1, choices = ["xml", "json"], style = wx.CB_READONLY)
        danmaku_type_cb.SetSelection(0)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(danmaku_type_lb, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, 10)
        hbox.Add(danmaku_type_cb, 0, wx.ALL & (~wx.TOP), 10)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(down_danmaku_chk, 0, wx.ALL, 10)
        vbox.Add(hbox)

        danmaku_sbox = wx.StaticBoxSizer(danmaku_box)
        danmaku_sbox.Add(vbox)

        self.vbox.Add(danmaku_sbox, 0, wx.ALL | wx.EXPAND, 10)