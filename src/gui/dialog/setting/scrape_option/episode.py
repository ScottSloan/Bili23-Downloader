import wx

from utils.config import Config
from utils.common.map import nfo_type_map

from gui.component.panel.panel import Panel
from gui.component.choice.choice import Choice
from gui.component.staticbitmap.staticbitmap import StaticBitmap

class EpisodePage(Panel):
    def __init__(self, parent: wx.Window):
        Panel.__init__(self, parent)

        self.init_UI()

        self.init_data()

    def init_UI(self):
        nfo_type_lab = wx.StaticText(self, -1, "NFO 文件格式")
        self.nfo_type_choice = Choice(self)
        self.nfo_type_choice.SetChoices(nfo_type_map)

        nfo_type_hbox = wx.BoxSizer(wx.HORIZONTAL)
        nfo_type_hbox.Add(nfo_type_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        nfo_type_hbox.Add(self.nfo_type_choice, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        nfo_file_lab = wx.StaticText(self, -1, "创建 NFO 文件")
        
        self.tvshow_nfo_lab = wx.StaticText(self, -1, "剧集")
        self.tvshow_nfo_chk = wx.CheckBox(self, -1, "tvshow.nfo")
        self.season_nfo_lab = wx.StaticText(self, -1, "季")
        self.season_nfo_chk = wx.CheckBox(self, -1, "season.nfo")
        self.episode_nfo_lab = wx.StaticText(self, -1, "集")
        self.episode_nfo_chk = wx.CheckBox(self, -1, "<剧集文件名>.nfo")

        nfo_file_grid_box = wx.FlexGridSizer(3, 2, 0, 0)
        nfo_file_grid_box.Add(self.tvshow_nfo_lab, 0, wx.ALL, self.FromDIP(6))
        nfo_file_grid_box.Add(self.tvshow_nfo_chk, 0, wx.ALL, self.FromDIP(6))
        nfo_file_grid_box.Add(self.season_nfo_lab, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        nfo_file_grid_box.Add(self.season_nfo_chk, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        nfo_file_grid_box.Add(self.episode_nfo_lab, 0, wx.ALL & (~wx.TOP) , self.FromDIP(6))
        nfo_file_grid_box.Add(self.episode_nfo_chk, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))

        nfo_file_hbox = wx.BoxSizer(wx.HORIZONTAL)
        nfo_file_hbox.AddSpacer(self.FromDIP(20))
        nfo_file_hbox.Add(nfo_file_grid_box, 0, wx.EXPAND)

        nfo_file_vbox = wx.BoxSizer(wx.VERTICAL)
        nfo_file_vbox.Add(nfo_file_lab, 0, wx.ALL & (~wx.BOTTOM) & (~wx.TOP), self.FromDIP(6))
        nfo_file_vbox.Add(nfo_file_hbox, 0, wx.EXPAND)

        self.warning_icon = StaticBitmap(self, bmp = wx.ArtProvider.GetBitmap(wx.ART_WARNING, size = self.FromDIP((16, 16))), size = self.FromDIP((16, 16)))
        self.warning_lab = wx.StaticText(self, -1, "未启用严格刮削命名模板，无法更改设置")
        self.warning_lab.Wrap(self.FromDIP(200))

        warning_hbox = wx.BoxSizer(wx.HORIZONTAL)
        warning_hbox.Add(self.warning_icon, 0, wx.ALL & (~wx.RIGHT) | wx.ALIGN_CENTER, self.FromDIP(6))
        warning_hbox.Add(self.warning_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        
        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(nfo_type_hbox, 0, wx.EXPAND)
        vbox.Add(nfo_file_vbox, 0, wx.EXPAND)
        vbox.Add(warning_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def init_data(self):
        option = Config.Temp.scrape_option.get("episode")

        self.nfo_type_choice.SetCurrentSelection(option.get("nfo_file_type", 0))
        self.tvshow_nfo_chk.SetValue(option.get("download_tvshow_nfo", False))
        self.season_nfo_chk.SetValue(option.get("download_season_nfo", False))
        self.episode_nfo_chk.SetValue(option.get("download_episode_nfo", False))

        self.check_strict_naming()

    def save(self):
        return {
            "episode": {
                "nfo_file_type": self.nfo_type_choice.GetSelection(),
                "download_tvshow_nfo": self.tvshow_nfo_chk.GetValue(),
                "download_season_nfo": self.season_nfo_chk.GetValue(),
                "download_episode_nfo": self.episode_nfo_chk.GetValue(),
            }
        }
    
    def disable_tvshow_chk(self):
        self.tvshow_nfo_lab.Disable()
        self.tvshow_nfo_chk.Disable()

    def disable_season_chk(self):
        self.season_nfo_lab.Disable()
        self.season_nfo_chk.Disable()

    def disable_episode_chk(self):
        self.episode_nfo_lab.Disable()
        self.episode_nfo_chk.Disable()

    def show_warn_icon(self, show: bool):
        if show:
            self.warning_icon.Show()
            self.warning_lab.Show()
        else:
            self.warning_icon.Hide()
            self.warning_lab.Hide()

        self.Layout()
    
    def check_strict_naming(self):
        if not Config.Temp.strict_naming:
            self.disable_tvshow_chk()
            self.disable_season_chk()
            self.disable_episode_chk()

            self.tvshow_nfo_chk.SetValue(False)
            self.season_nfo_chk.SetValue(False)
            self.episode_nfo_chk.SetValue(False)

            self.show_warn_icon(True)
        else:
            self.show_warn_icon(False)
