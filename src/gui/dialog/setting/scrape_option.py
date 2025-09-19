import wx

from utils.config import Config
from utils.common.map import nfo_type_map

from gui.component.window.dialog import Dialog
from gui.component.choice.choice import Choice

class ScrapeOptionDialog(Dialog):
    def __init__(self, parent: wx.Window):
        Dialog.__init__(self, parent, "刮削设置")

        self.init_UI()

        self.init_data()

        self.CenterOnParent()

    def init_UI(self):
        nfo_type_lab = wx.StaticText(self, -1, "NFO 文件格式")
        self.nfo_type_choice = Choice(self)
        self.nfo_type_choice.SetChoices(nfo_type_map)

        nfo_type_hbox = wx.BoxSizer(wx.HORIZONTAL)
        nfo_type_hbox.Add(nfo_type_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        nfo_type_hbox.Add(self.nfo_type_choice, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        nfo_file_lab = wx.StaticText(self, -1, "创建 NFO 文件")

        tvshow_nfo_lab = wx.StaticText(self, -1, "剧集")
        self.tvshow_nfo_chk = wx.CheckBox(self, -1, "tvshow.nfo")
        season_nfo_lab = wx.StaticText(self, -1, "季")
        self.season_nfo_chk = wx.CheckBox(self, -1, "season.nfo")
        episode_nfo_lab = wx.StaticText(self, -1, "集")
        self.episode_nfo_chk = wx.CheckBox(self, -1, "<SxxExx>.nfo")

        nfo_file_grid_box = wx.FlexGridSizer(3, 2, 0, 0)
        nfo_file_grid_box.Add(tvshow_nfo_lab, 0, wx.ALL, self.FromDIP(6))
        nfo_file_grid_box.Add(self.tvshow_nfo_chk, 0, wx.ALL, self.FromDIP(6))
        nfo_file_grid_box.Add(season_nfo_lab, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        nfo_file_grid_box.Add(self.season_nfo_chk, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        nfo_file_grid_box.Add(episode_nfo_lab, 0, wx.ALL & (~wx.TOP) , self.FromDIP(6))
        nfo_file_grid_box.Add(self.episode_nfo_chk, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))

        nfo_file_hbox = wx.BoxSizer(wx.HORIZONTAL)
        nfo_file_hbox.AddSpacer(self.FromDIP(20))
        nfo_file_hbox.Add(nfo_file_grid_box, 0, wx.EXPAND)

        nfo_file_vbox = wx.BoxSizer(wx.VERTICAL)
        nfo_file_vbox.Add(nfo_file_lab, 0, wx.ALL & (~wx.BOTTOM) & (~wx.TOP), self.FromDIP(6))
        nfo_file_vbox.Add(nfo_file_hbox, 0, wx.EXPAND)

        self.ok_btn = wx.Button(self, wx.ID_OK, "确定", size = self.get_scaled_size((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, "取消", size = self.get_scaled_size((80, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer(1)
        bottom_hbox.Add(self.ok_btn, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        bottom_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(nfo_type_hbox, 0, wx.EXPAND)
        vbox.Add(nfo_file_vbox, 0, wx.EXPAND)
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def init_data(self):
        self.nfo_type_choice.SetSelection(Config.Basic.nfo_file_type)

    def set_option(self):
        Config.Basic.nfo_file_type = self.nfo_type_choice.GetSelection()