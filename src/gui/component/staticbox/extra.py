import wx

from utils.common.map import danmaku_format_map, subtitle_format_map, cover_format_map

from gui.component.panel.panel import Panel

class ExtraStaticBox(Panel):
    def __init__(self, parent):
        Panel.__init__(self, parent)

        self.init_UI()

    def init_UI(self):
        extra_box = wx.StaticBox(self, -1, "附加内容下载选项")

        self.download_danmaku_file_chk = wx.CheckBox(extra_box, -1, "下载视频弹幕")
        self.danmaku_file_type_lab = wx.StaticText(extra_box, -1, "弹幕文件格式")
        self.danmaku_file_type_choice = wx.Choice(extra_box, -1, choices = list(danmaku_format_map.keys()))

        danmaku_hbox = wx.BoxSizer(wx.HORIZONTAL)
        danmaku_hbox.AddSpacer(self.FromDIP(20))
        danmaku_hbox.Add(self.danmaku_file_type_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        danmaku_hbox.Add(self.danmaku_file_type_choice, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))
        danmaku_hbox.AddSpacer(self.FromDIP(60))

        self.download_subtitle_file_chk = wx.CheckBox(extra_box, -1, "下载视频字幕")
        self.subtitle_file_type_lab = wx.StaticText(extra_box, -1, "字幕文件格式")
        self.subtitle_file_type_choice = wx.Choice(extra_box, -1, choices = list(subtitle_format_map.keys()))
        self.subtitle_file_lan_type_lab = wx.StaticText(extra_box, -1, "字幕语言")
        self.subtitle_file_lan_type_btn = wx.Button(extra_box, -1, "自定义")

        subtitle_grid_box = wx.FlexGridSizer(2, 4, 0, 0)
        subtitle_grid_box.AddSpacer(self.FromDIP(20))
        subtitle_grid_box.Add(self.subtitle_file_type_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
        subtitle_grid_box.Add(self.subtitle_file_type_choice, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))
        subtitle_grid_box.AddSpacer(self.FromDIP(20))
        subtitle_grid_box.AddSpacer(self.FromDIP(20))
        subtitle_grid_box.Add(self.subtitle_file_lan_type_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
        subtitle_grid_box.Add(self.subtitle_file_lan_type_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))
        subtitle_grid_box.AddSpacer(self.FromDIP(20))

        self.download_cover_file_chk = wx.CheckBox(extra_box, -1, "下载视频封面")
        self.cover_file_type_lab = wx.StaticText(extra_box, -1, "封面文件格式")
        self.cover_file_type_choice = wx.Choice(extra_box, -1, choices = list(cover_format_map.keys()))

        cover_hbox = wx.BoxSizer(wx.HORIZONTAL)
        cover_hbox.AddSpacer(self.FromDIP(20))
        cover_hbox.Add(self.cover_file_type_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        cover_hbox.Add(self.cover_file_type_choice, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))
        cover_hbox.AddSpacer(self.FromDIP(60))

        extra_sbox = wx.StaticBoxSizer(extra_box, wx.VERTICAL)
        extra_sbox.AddSpacer(self.FromDIP(6))
        extra_sbox.Add(self.download_danmaku_file_chk, 0, wx.ALL & (~wx.BOTTOM), self.FromDIP(6))
        extra_sbox.Add(danmaku_hbox, 0, wx.EXPAND)
        extra_sbox.Add(self.download_subtitle_file_chk, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        extra_sbox.Add(subtitle_grid_box, 0, wx.EXPAND)
        extra_sbox.Add(self.download_cover_file_chk, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM), self.FromDIP(6))
        extra_sbox.Add(cover_hbox, 0, wx.EXPAND)
        extra_sbox.AddSpacer(self.FromDIP(6))

        self.SetSizer(extra_sbox)