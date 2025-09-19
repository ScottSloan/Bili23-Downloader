import wx

from utils.config import Config

from utils.common.map import danmaku_format_map, subtitle_format_map, cover_format_map, metadata_format_map
from utils.common.style.icon_v4 import Icon, IconID

from gui.dialog.setting.custom_subtitle_lan import CustomLanDialog
from gui.dialog.setting.scrape_option import ScrapeOptionDialog
from gui.dialog.setting.ass_style.custom_ass_style_v2 import CustomASSStyleDialog

from gui.component.panel.panel import Panel
from gui.component.button.bitmap_button import BitmapButton

class ExtraStaticBox(Panel):
    def __init__(self, parent: wx.Window, parent_window: wx.Window, is_setting_page: bool):
        self.parent_window = parent_window
        self.is_setting_page = is_setting_page

        Panel.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

    def init_UI(self):
        extra_box = wx.StaticBox(self, -1, "附加内容下载选项")

        self.download_danmaku_file_chk = wx.CheckBox(extra_box, -1, "下载视频弹幕")
        self.danmaku_file_type_lab = wx.StaticText(extra_box, -1, "弹幕文件格式")
        self.danmaku_file_type_choice = wx.Choice(extra_box, -1, choices = list(danmaku_format_map.keys()))
        
        danmaku_hbox = wx.BoxSizer(wx.HORIZONTAL)
        danmaku_hbox.AddSpacer(self.FromDIP(20))
        danmaku_hbox.Add(self.danmaku_file_type_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        danmaku_hbox.Add(self.danmaku_file_type_choice, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        danmuku_vbox = wx.BoxSizer(wx.VERTICAL)
        danmuku_vbox.Add(self.download_danmaku_file_chk, 0, wx.ALL & (~wx.BOTTOM), self.FromDIP(6))
        danmuku_vbox.Add(danmaku_hbox, 0, wx.EXPAND)

        self.download_subtitle_file_chk = wx.CheckBox(extra_box, -1, "下载视频字幕")
        self.subtitle_file_type_lab = wx.StaticText(extra_box, -1, "字幕文件格式")
        self.subtitle_file_type_choice = wx.Choice(extra_box, -1, choices = list(subtitle_format_map.keys()))
        self.subtitle_file_lan_type_btn = BitmapButton(extra_box, Icon.get_icon_bitmap(IconID.Setting), tooltip = "自定义字幕语言")

        subtitle_hbox = wx.BoxSizer(wx.HORIZONTAL)
        subtitle_hbox.AddSpacer(self.FromDIP(20))
        subtitle_hbox.Add(self.subtitle_file_type_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
        subtitle_hbox.Add(self.subtitle_file_type_choice, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        subtitle_hbox.Add(self.subtitle_file_lan_type_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        subtitle_vbox = wx.BoxSizer(wx.VERTICAL)
        subtitle_vbox.Add(self.download_subtitle_file_chk, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        subtitle_vbox.Add(subtitle_hbox, 0, wx.EXPAND)

        self.download_cover_file_chk = wx.CheckBox(extra_box, -1, "下载视频封面")
        self.cover_file_type_lab = wx.StaticText(extra_box, -1, "封面文件格式")
        self.cover_file_type_choice = wx.Choice(extra_box, -1, choices = list(cover_format_map.keys()))

        cover_hbox = wx.BoxSizer(wx.HORIZONTAL)
        cover_hbox.AddSpacer(self.FromDIP(20))
        cover_hbox.Add(self.cover_file_type_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        cover_hbox.Add(self.cover_file_type_choice, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        cover_vbox = wx.BoxSizer(wx.VERTICAL)
        cover_vbox.Add(self.download_cover_file_chk, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM), self.FromDIP(6))
        cover_vbox.Add(cover_hbox, 0, wx.EXPAND)

        self.download_metadata_file_chk = wx.CheckBox(extra_box, -1, "下载视频元数据")
        self.metadata_file_type_lab = wx.StaticText(extra_box, -1, "元数据文件格式")
        self.metadata_file_type_choice = wx.Choice(extra_box, -1, choices = list(metadata_format_map.keys()))
        self.metadata_file_scrape_option_btn = BitmapButton(extra_box, Icon.get_icon_bitmap(IconID.Setting), tooltip = "刮削设置")

        metadata_hbox = wx.BoxSizer(wx.HORIZONTAL)
        metadata_hbox.AddSpacer(self.FromDIP(20))
        metadata_hbox.Add(self.metadata_file_type_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        metadata_hbox.Add(self.metadata_file_type_choice, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        metadata_hbox.Add(self.metadata_file_scrape_option_btn, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        metadata_vbox = wx.BoxSizer(wx.VERTICAL)
        metadata_vbox.Add(self.download_metadata_file_chk, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM), self.FromDIP(6))
        metadata_vbox.Add(metadata_hbox, 0, wx.EXPAND)

        self.custom_ass_style_btn = wx.Button(extra_box, -1, "自定义 ASS 样式", size = self.get_scaled_size((120, 28)))

        extra_sbox = wx.StaticBoxSizer(extra_box, wx.VERTICAL)
        extra_sbox.AddStretchSpacer()
        extra_sbox.Add(danmuku_vbox, 0, wx.EXPAND)
        extra_sbox.Add(subtitle_vbox, 0, wx.EXPAND)
        extra_sbox.Add(cover_vbox, 0, wx.EXPAND)
        extra_sbox.Add(metadata_vbox, 0, wx.EXPAND)
        extra_sbox.Add(self.custom_ass_style_btn, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        extra_sbox.AddStretchSpacer()

        self.SetSizer(extra_sbox)

    def Bind_EVT(self):
        self.download_danmaku_file_chk.Bind(wx.EVT_CHECKBOX, self.onCheckDownloadDanmakuEVT)
        self.download_subtitle_file_chk.Bind(wx.EVT_CHECKBOX, self.onCheckDownloadSubtitleEVT)
        self.download_cover_file_chk.Bind(wx.EVT_CHECKBOX, self.onCheckDownloadCoverEVT)
        self.download_metadata_file_chk.Bind(wx.EVT_CHECKBOX, self.onCheckDownloadMetadataEVT)

        self.subtitle_file_lan_type_btn.Bind(wx.EVT_BUTTON, self.onCustomSubtitleLanEVT)
        self.metadata_file_scrape_option_btn.Bind(wx.EVT_BUTTON, self.onMetaDataScrapeOptionEVT)

        self.custom_ass_style_btn.Bind(wx.EVT_BUTTON, self.onCustomASSStyleEVT)

    def load_data(self):
        Config.Temp.ass_style = Config.Basic.ass_style.copy()

        self.download_danmaku_file_chk.SetValue(Config.Basic.download_danmaku_file)
        self.danmaku_file_type_choice.Select(Config.Basic.danmaku_file_type)
        self.download_subtitle_file_chk.SetValue(Config.Basic.download_subtitle_file)
        self.subtitle_file_type_choice.Select(Config.Basic.subtitle_file_type)
        self.download_cover_file_chk.SetValue(Config.Basic.download_cover_file)
        self.cover_file_type_choice.Select(Config.Basic.cover_file_type)
        self.download_metadata_file_chk.SetValue(Config.Basic.download_metadata_file)
        self.metadata_file_type_choice.Select(Config.Basic.metadata_file_type)

        self.onCheckDownloadDanmakuEVT(0)
        self.onCheckDownloadSubtitleEVT(0)
        self.onCheckDownloadCoverEVT(0)
        self.onCheckDownloadMetadataEVT(0)

    def save(self):
        Config.Basic.ass_style = Config.Temp.ass_style.copy()

        Config.Basic.download_danmaku_file = self.download_danmaku_file_chk.GetValue()
        Config.Basic.danmaku_file_type = self.danmaku_file_type_choice.GetSelection()
        Config.Basic.download_subtitle_file = self.download_subtitle_file_chk.GetValue()
        Config.Basic.subtitle_file_type = self.subtitle_file_type_choice.GetSelection()
        Config.Basic.download_cover_file = self.download_cover_file_chk.GetValue()
        Config.Basic.cover_file_type = self.cover_file_type_choice.GetSelection()
        Config.Basic.download_metadata_file = self.download_metadata_file_chk.GetValue()
        Config.Basic.metadata_file_type = self.metadata_file_type_choice.GetSelection()

    def onCheckDownloadDanmakuEVT(self, event):
        enable = self.download_danmaku_file_chk.GetValue()

        self.danmaku_file_type_lab.Enable(enable)
        self.danmaku_file_type_choice.Enable(enable)

    def onCheckDownloadSubtitleEVT(self, event):
        enable = self.download_subtitle_file_chk.GetValue()

        self.subtitle_file_type_lab.Enable(enable)
        self.subtitle_file_type_choice.Enable(enable)
        self.subtitle_file_lan_type_btn.Enable(enable)

    def onCheckDownloadCoverEVT(self, event):
        enable = self.download_cover_file_chk.GetValue()

        self.cover_file_type_lab.Enable(enable)
        self.cover_file_type_choice.Enable(enable)

    def onCheckDownloadMetadataEVT(self, event):
        enable = self.download_metadata_file_chk.GetValue()

        self.metadata_file_type_lab.Enable(enable)
        self.metadata_file_type_choice.Enable(enable)
        self.metadata_file_scrape_option_btn.Enable(enable)

    def onCustomSubtitleLanEVT(self, event):
        dlg = CustomLanDialog(self.parent_window)

        if dlg.ShowModal() == wx.ID_OK:
            dlg.set_option()

    def onMetaDataScrapeOptionEVT(self, event):
        dlg = ScrapeOptionDialog(self.parent_window)

        if dlg.ShowModal() == wx.ID_OK:
            dlg.set_option()

    def onCustomASSStyleEVT(self, event):
        dlg = CustomASSStyleDialog(self.parent_window)
        dlg.ShowModal()