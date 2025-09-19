import wx

from utils.config import Config
from utils.common.map import nfo_type_map

from gui.component.panel.panel import Panel
from gui.component.choice.choice import Choice

class LessonPage(Panel):
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

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(nfo_type_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def init_data(self):
        option = Config.Temp.scrape_option.get("lesson")

        self.nfo_type_choice.SetCurrentSelection(option.get("nfo_file_type", 0))

    def save(self):
        return {
            "lesson": {
                "nfo_file_type": self.nfo_type_choice.GetSelection()
            }
        }
