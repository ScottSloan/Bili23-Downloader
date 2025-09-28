import wx

from utils.config import Config

from gui.dialog.setting.scrape_option.add_date_box import AddDateBox

from gui.component.panel.panel import Panel
from gui.component.staticbitmap.staticbitmap import StaticBitmap

class EpisodePage(Panel):
    def __init__(self, parent: wx.Window):
        Panel.__init__(self, parent)

        self.init_UI()

        self.init_data()

    def init_UI(self):
        self.add_date_source_box = AddDateBox(self)

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

        tip_icon = StaticBitmap(self, bmp = wx.ArtProvider.GetBitmap(wx.ART_INFORMATION, size = self.FromDIP((16, 16))), size = self.FromDIP((16, 16)))
        tip_lab = wx.StaticText(self, -1, "如果需要将剧集分季存放至不同文件夹\n请启用“严格刮削命名模板”选项")

        tip_hbox = wx.BoxSizer(wx.HORIZONTAL)
        tip_hbox.Add(tip_icon, 0, wx.ALL & (~wx.RIGHT) | wx.ALIGN_CENTER, self.FromDIP(6))
        tip_hbox.Add(tip_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.add_date_source_box, 0, wx.EXPAND)
        vbox.Add(nfo_file_vbox, 0, wx.EXPAND)
        vbox.AddSpacer(self.FromDIP(5))
        vbox.Add(tip_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def init_data(self):
        option = Config.Temp.scrape_option.get("episode")

        self.add_date_source_box.init_data(option)

        self.tvshow_nfo_chk.SetValue(option.get("download_tvshow_nfo", False))
        self.season_nfo_chk.SetValue(option.get("download_season_nfo", False))
        self.episode_nfo_chk.SetValue(option.get("download_episode_nfo", False))

    def save(self):
        return {
            "episode": {
                **self.add_date_source_box.save(),
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
