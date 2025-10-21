import wx
import gettext

from utils.config import Config

from gui.dialog.setting.scrape_option.add_date_box import AddDateBox

from gui.component.panel.panel import Panel

_ = gettext.gettext

class MoviePage(Panel):
    def __init__(self, parent: wx.Window):
        Panel.__init__(self, parent)

        self.init_UI()

        self.init_data()

    def init_UI(self):
        self.add_date_source_box = AddDateBox(self)

        nfo_file_lab = wx.StaticText(self, -1, _("创建 NFO 文件"))
        
        self.movie_nfo_chk = wx.CheckBox(self, -1, "movie.nfo")
        self.episode_nfo_chk = wx.CheckBox(self, -1, _("<电影文件名>.nfo"))

        nfo_file_grid_box = wx.FlexGridSizer(2, 1, 0, 0)
        nfo_file_grid_box.Add(self.movie_nfo_chk, 0, wx.ALL, self.FromDIP(6))
        nfo_file_grid_box.Add(self.episode_nfo_chk, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))

        nfo_file_hbox = wx.BoxSizer(wx.HORIZONTAL)
        nfo_file_hbox.AddSpacer(self.FromDIP(20))
        nfo_file_hbox.Add(nfo_file_grid_box, 0, wx.EXPAND)

        nfo_file_vbox = wx.BoxSizer(wx.VERTICAL)
        nfo_file_vbox.Add(nfo_file_lab, 0, wx.ALL & (~wx.BOTTOM) & (~wx.TOP), self.FromDIP(6))
        nfo_file_vbox.Add(nfo_file_hbox, 0, wx.EXPAND)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.add_date_source_box, 0, wx.EXPAND)
        vbox.Add(nfo_file_vbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def init_data(self):
        option = Config.Temp.scrape_option.get("movie")

        self.add_date_source_box.init_data(option)

        self.movie_nfo_chk.SetValue(option.get("download_movie_nfo", False))
        self.episode_nfo_chk.SetValue(option.get("download_episode_nfo", False))

    def save(self):
        return {
            "movie": {
                **self.add_date_source_box.save(),
                "download_movie_nfo": self.movie_nfo_chk.GetValue(),
                "download_episode_nfo": self.episode_nfo_chk.GetValue(),
            }
        }
