import wx

from utils.config import Config

from utils.common.map import danmaku_format_map, subtitle_format_map, cover_format_map

from gui.dialog.setting.custom_subtitle_lan import CustomLanDialog
from gui.dialog.setting.custom_ass_style import CustomASSStyleDialog

from gui.component.panel.panel import Panel

from gui.component.misc.tooltip import ToolTip

class ExtraStaticBox(Panel):
    def __init__(self, parent, is_setting_page: bool):
        self.is_setting_page = is_setting_page

        Panel.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

    def init_UI(self):
        extra_box = wx.StaticBox(self, -1, "附加内容下载选项")

        self.download_danmaku_file_chk = wx.CheckBox(extra_box, -1, "下载视频弹幕")
        self.danmaku_file_type_lab = wx.StaticText(extra_box, -1, "弹幕文件格式")
        self.danmaku_file_type_choice = wx.Choice(extra_box, -1, choices = list(danmaku_format_map.keys()))
        danmaku_tooltip = ToolTip(extra_box)
        danmaku_tooltip.set_tooltip("ASS 格式弹幕支持自定义样式，请在设置窗口中进行修改\n\n找不到设置窗口的，请仔细阅读程序使用说明")
        danmaku_tooltip.Show(not self.is_setting_page)

        danmaku_hbox = wx.BoxSizer(wx.HORIZONTAL)
        danmaku_hbox.AddSpacer(self.FromDIP(20))
        danmaku_hbox.Add(self.danmaku_file_type_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        danmaku_hbox.Add(self.danmaku_file_type_choice, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))
        danmaku_hbox.Add(danmaku_tooltip, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.download_subtitle_file_chk = wx.CheckBox(extra_box, -1, "下载视频字幕")
        self.subtitle_file_type_lab = wx.StaticText(extra_box, -1, "字幕文件格式")
        self.subtitle_file_type_choice = wx.Choice(extra_box, -1, choices = list(subtitle_format_map.keys()))
        subtitle_tooltip = ToolTip(extra_box)
        subtitle_tooltip.set_tooltip("ASS 格式字幕支持自定义样式，请在设置窗口中进行修改\n\n找不到设置窗口的，请仔细阅读程序使用说明")
        subtitle_tooltip.Show(not self.is_setting_page)

        subtitle_type_hbox = wx.BoxSizer(wx.HORIZONTAL)
        subtitle_type_hbox.Add(self.subtitle_file_type_choice, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))
        subtitle_type_hbox.Add(subtitle_tooltip, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.subtitle_file_lan_type_lab = wx.StaticText(extra_box, -1, "字幕语言")
        self.subtitle_file_lan_type_btn = wx.Button(extra_box, -1, "自定义")

        subtitle_grid_box = wx.FlexGridSizer(2, 4, 0, 0)
        subtitle_grid_box.AddSpacer(self.FromDIP(20))
        subtitle_grid_box.Add(self.subtitle_file_type_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
        subtitle_grid_box.Add(subtitle_type_hbox, 0, wx.EXPAND)
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

        self.custom_ass_style_btn = wx.Button(extra_box, -1, "自定义 ASS 样式", size = self.get_scaled_size((120, 28)))

        extra_sbox = wx.StaticBoxSizer(extra_box, wx.VERTICAL)
        extra_sbox.AddStretchSpacer()
        extra_sbox.Add(self.download_danmaku_file_chk, 0, wx.ALL & (~wx.BOTTOM), self.FromDIP(6))
        extra_sbox.Add(danmaku_hbox, 0, wx.EXPAND)
        extra_sbox.Add(self.download_subtitle_file_chk, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        extra_sbox.Add(subtitle_grid_box, 0, wx.EXPAND)
        extra_sbox.Add(self.download_cover_file_chk, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM), self.FromDIP(6))
        extra_sbox.Add(cover_hbox, 0, wx.EXPAND)
        extra_sbox.Add(self.custom_ass_style_btn, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        extra_sbox.AddStretchSpacer()

        self.SetSizer(extra_sbox)

    def Bind_EVT(self):
        self.download_danmaku_file_chk.Bind(wx.EVT_CHECKBOX, self.onCheckDownloadDanmakuEVT)
        self.download_subtitle_file_chk.Bind(wx.EVT_CHECKBOX, self.onCheckDownloadSubtitleEVT)
        self.download_cover_file_chk.Bind(wx.EVT_CHECKBOX, self.onCheckDownloadCoverEVT)

        self.subtitle_file_lan_type_btn.Bind(wx.EVT_BUTTON, self.onCustomSubtitleLanEVT)

        self.custom_ass_style_btn.Bind(wx.EVT_BUTTON, self.onCustomASSStyleEVT)

    def load_data(self):
        self.download_danmaku_file_chk.SetValue(Config.Basic.download_danmaku_file)
        self.danmaku_file_type_choice.Select(Config.Basic.danmaku_file_type)
        self.download_subtitle_file_chk.SetValue(Config.Basic.download_subtitle_file)
        self.subtitle_file_type_choice.Select(Config.Basic.subtitle_file_type)
        self.download_cover_file_chk.SetValue(Config.Basic.download_cover_file)
        self.cover_file_type_choice.Select(Config.Basic.cover_file_type)

        self.onCheckDownloadDanmakuEVT(0)
        self.onCheckDownloadSubtitleEVT(0)
        self.onCheckDownloadCoverEVT(0)
    
    def save(self):
        Config.Basic.download_danmaku_file = self.download_danmaku_file_chk.GetValue()
        Config.Basic.danmaku_file_type = self.danmaku_file_type_choice.GetSelection()
        Config.Basic.download_subtitle_file = self.download_subtitle_file_chk.GetValue()
        Config.Basic.subtitle_file_type = self.subtitle_file_type_choice.GetSelection()
        Config.Basic.download_cover_file = self.download_cover_file_chk.GetValue()
        Config.Basic.cover_file_type = self.cover_file_type_choice.GetSelection()

    def onCheckDownloadDanmakuEVT(self, event):
        enable = self.download_danmaku_file_chk.GetValue()

        self.danmaku_file_type_lab.Enable(enable)
        self.danmaku_file_type_choice.Enable(enable)

    def onCheckDownloadSubtitleEVT(self, event):
        enable = self.download_subtitle_file_chk.GetValue()

        self.subtitle_file_type_lab.Enable(enable)
        self.subtitle_file_type_choice.Enable(enable)
        self.subtitle_file_lan_type_lab.Enable(enable)
        self.subtitle_file_lan_type_btn.Enable(enable)

    def onCheckDownloadCoverEVT(self, event):
        enable = self.download_cover_file_chk.GetValue()

        self.cover_file_type_lab.Enable(enable)
        self.cover_file_type_choice.Enable(enable)

    def onCustomSubtitleLanEVT(self, event):
        dlg = CustomLanDialog(self.GetParent())

        if dlg.ShowModal() == wx.ID_OK:
            dlg.set_option()

    def onCustomASSStyleEVT(self, event):
        dlg = CustomASSStyleDialog(self.GetParent())
        dlg.ShowModal()