import wx
import gettext

from utils.config import Config

from utils.common.map import danmaku_format_map, subtitle_format_map, cover_format_map, metadata_format_map
from utils.common.style.icon_v4 import Icon, IconID

from gui.dialog.setting.custom_subtitle_lan import CustomLanDialog
from gui.dialog.setting.scrape_option.scrape_option import ScrapeOptionDialog
from gui.dialog.setting.ass_style.custom_ass_style_v2 import CustomASSStyleDialog

from gui.component.panel.panel import Panel
from gui.component.button.bitmap_button import BitmapButton

_ = gettext.gettext

class ExtraStaticBox(Panel):
    def __init__(self, parent: wx.Window, parent_window: wx.Window, is_setting_page: bool):
        self.parent_window = parent_window
        self.is_setting_page = is_setting_page

        Panel.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

    def init_UI(self):
        extra_box = wx.StaticBox(self, -1, _("附加内容下载选项"))

        self.download_danmaku_file_chk = wx.CheckBox(extra_box, -1, _("下载视频弹幕"))
        self.danmaku_file_type_lab = wx.StaticText(extra_box, -1, _("弹幕文件格式"))
        self.danmaku_file_type_choice = wx.Choice(extra_box, -1, choices = list(danmaku_format_map.keys()))

        self.download_subtitle_file_chk = wx.CheckBox(extra_box, -1, _("下载视频字幕"))
        self.subtitle_file_type_lab = wx.StaticText(extra_box, -1, _("字幕文件格式"))
        self.subtitle_file_type_choice = wx.Choice(extra_box, -1, choices = list(subtitle_format_map.keys()))
        self.subtitle_file_lan_type_btn = BitmapButton(extra_box, Icon.get_icon_bitmap(IconID.Setting), tooltip = _("自定义字幕语言"))

        self.download_cover_file_chk = wx.CheckBox(extra_box, -1, _("下载视频封面"))
        self.cover_file_type_lab = wx.StaticText(extra_box, -1, _("封面文件格式"))
        self.cover_file_type_choice = wx.Choice(extra_box, -1, choices = list(cover_format_map.keys()))

        self.download_metadata_file_chk = wx.CheckBox(extra_box, -1, _("下载视频元数据"))
        self.metadata_file_type_lab = wx.StaticText(extra_box, -1, _("元数据文件格式"))
        self.metadata_file_type_choice = wx.Choice(extra_box, -1, choices = list(metadata_format_map.keys()))
        self.metadata_file_scrape_option_btn = BitmapButton(extra_box, Icon.get_icon_bitmap(IconID.Setting), tooltip = _("刮削设置"))

        extra_grid_sizer = wx.GridBagSizer(0, 0)
        extra_grid_sizer.Add(self.download_danmaku_file_chk, pos = (0, 0), span = (0, 3), flag = wx.ALL & (~wx.BOTTOM) | wx.ALIGN_CENTRE_VERTICAL, border = self.FromDIP(6))
        extra_grid_sizer.Add(wx.StaticText(extra_box, -1, size = self.FromDIP((20, -1))), pos = (1, 0), span = (0, 0))
        extra_grid_sizer.Add(self.danmaku_file_type_lab, pos = (1, 1), flag = wx.ALL | wx.ALIGN_CENTRE_VERTICAL, border = self.FromDIP(6))
        extra_grid_sizer.Add(self.danmaku_file_type_choice, pos = (1, 2), flag = wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTRE_VERTICAL, border = self.FromDIP(6))

        extra_grid_sizer.Add(self.download_subtitle_file_chk, pos = (2, 0), span = (0, 3), flag = wx.ALL & (~wx.BOTTOM) | wx.ALIGN_CENTRE_VERTICAL, border = self.FromDIP(6))
        extra_grid_sizer.Add(wx.StaticText(extra_box, -1, size = self.FromDIP((20, -1))), pos = (3, 0), span = (0, 0))
        extra_grid_sizer.Add(self.subtitle_file_type_lab, pos = (3, 1), flag = wx.ALL | wx.ALIGN_CENTRE_VERTICAL, border = self.FromDIP(6))
        extra_grid_sizer.Add(self.subtitle_file_type_choice, pos = (3, 2), flag = wx.ALL & (~wx.LEFT) | wx.EXPAND | wx.ALIGN_CENTRE_VERTICAL, border = self.FromDIP(6))
        extra_grid_sizer.Add(self.subtitle_file_lan_type_btn, pos = (3, 3), flag = wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTRE_VERTICAL, border = self.FromDIP(6))

        extra_grid_sizer.Add(self.download_cover_file_chk, pos = (4, 0), span = (0, 3), flag = wx.ALL & (~wx.BOTTOM) | wx.ALIGN_CENTRE_VERTICAL, border = self.FromDIP(6))
        extra_grid_sizer.Add(wx.StaticText(extra_box, -1, size = self.FromDIP((20, -1))), pos = (5, 0), span = (0, 0))
        extra_grid_sizer.Add(self.cover_file_type_lab, pos = (5, 1), flag = wx.ALL | wx.ALIGN_CENTRE_VERTICAL, border = self.FromDIP(6))
        extra_grid_sizer.Add(self.cover_file_type_choice, pos = (5, 2), flag = wx.ALL & (~wx.LEFT) | wx.EXPAND | wx.ALIGN_CENTRE_VERTICAL, border = self.FromDIP(6))

        extra_grid_sizer.Add(self.download_metadata_file_chk, pos = (6, 0), span = (0, 3), flag = wx.ALL & (~wx.BOTTOM) | wx.ALIGN_CENTRE_VERTICAL, border = self.FromDIP(6))
        extra_grid_sizer.Add(wx.StaticText(extra_box, -1, size = self.FromDIP((20, -1))), pos = (7, 0), span = (0, 0))
        extra_grid_sizer.Add(self.metadata_file_type_lab, pos = (7, 1), flag = wx.ALL | wx.ALIGN_CENTRE_VERTICAL, border = self.FromDIP(6))
        extra_grid_sizer.Add(self.metadata_file_type_choice, pos = (7, 2), flag = wx.ALL & (~wx.LEFT) | wx.EXPAND | wx.ALIGN_CENTRE_VERTICAL, border = self.FromDIP(6))
        extra_grid_sizer.Add(self.metadata_file_scrape_option_btn, pos = (7, 3), flag = wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTRE_VERTICAL, border = self.FromDIP(6))

        self.custom_ass_style_btn = wx.Button(extra_box, -1, _("自定义 ASS 样式"), size = self.get_scaled_size((120, 28)))

        extra_sbox = wx.StaticBoxSizer(extra_box, wx.VERTICAL)
        extra_sbox.AddStretchSpacer()
        extra_sbox.Add(extra_grid_sizer, 0, wx.EXPAND)
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
        Config.Temp.scrape_option = Config.Basic.scrape_option.copy()
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
        Config.Basic.scrape_option = Config.Temp.scrape_option.copy()
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
        dlg.ShowModal()

    def onMetaDataScrapeOptionEVT(self, event):
        dlg = ScrapeOptionDialog(self.parent_window)
        dlg.ShowModal()

    def onCustomASSStyleEVT(self, event):
        dlg = CustomASSStyleDialog(self.parent_window)
        dlg.ShowModal()