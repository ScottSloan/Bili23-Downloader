import wx

from utils.config import Config
from utils.common.map import nfo_type_map

from gui.component.panel.panel import Panel
from gui.component.choice.choice import Choice
from gui.component.staticbitmap.staticbitmap import StaticBitmap

class MoviePage(Panel):
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
        
        self.movie_nfo_chk = wx.CheckBox(self, -1, "movie.nfo")
        self.episode_nfo_chk = wx.CheckBox(self, -1, "<电影文件名>.nfo")

        nfo_file_grid_box = wx.FlexGridSizer(2, 1, 0, 0)
        nfo_file_grid_box.Add(self.movie_nfo_chk, 0, wx.ALL, self.FromDIP(6))
        nfo_file_grid_box.Add(self.episode_nfo_chk, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))

        nfo_file_hbox = wx.BoxSizer(wx.HORIZONTAL)
        nfo_file_hbox.AddSpacer(self.FromDIP(20))
        nfo_file_hbox.Add(nfo_file_grid_box, 0, wx.EXPAND)

        nfo_file_vbox = wx.BoxSizer(wx.VERTICAL)
        nfo_file_vbox.Add(nfo_file_lab, 0, wx.ALL & (~wx.BOTTOM) & (~wx.TOP), self.FromDIP(6))
        nfo_file_vbox.Add(nfo_file_hbox, 0, wx.EXPAND)

        self.warning_icon = StaticBitmap(self, bmp = wx.ArtProvider.GetBitmap(wx.ART_WARNING, size = self.FromDIP((16, 16))), size = self.FromDIP((16, 16)))
        self.warning_lab = wx.StaticText(self, -1, "未启用严格刮削命名模板，无\n法更改设置")
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
        option = Config.Temp.scrape_option.get("movie")

        self.nfo_type_choice.SetCurrentSelection(option.get("nfo_file_type", 0))
        self.movie_nfo_chk.SetValue(option.get("download_movie_nfo", False))
        self.episode_nfo_chk.SetValue(option.get("download_episode_nfo", False))

        self.check_strict_naming()

    def save(self):
        return {
            "movie": {
                "nfo_file_type": self.nfo_type_choice.GetSelection(),
                "download_movie_nfo": self.movie_nfo_chk.GetValue(),
                "download_episode_nfo": self.episode_nfo_chk.GetValue(),
            }
        }
    
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
            self.movie_nfo_chk.Disable()
            self.episode_nfo_chk.Disable()

            self.movie_nfo_chk.SetValue(False)
            self.episode_nfo_chk.SetValue(False)

            self.show_warn_icon(True)
        else:
            self.show_warn_icon(False)
