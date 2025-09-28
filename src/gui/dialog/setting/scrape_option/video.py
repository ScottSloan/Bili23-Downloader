import wx

from utils.config import Config

from gui.dialog.setting.scrape_option.add_date_box import AddDateBox

from gui.component.panel.panel import Panel

class VideoPage(Panel):
    def __init__(self, parent: wx.Window):
        Panel.__init__(self, parent)

        self.init_UI()

        self.init_data()

    def init_UI(self):
        self.add_date_source_box = AddDateBox(self)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.add_date_source_box, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def init_data(self):
        option = Config.Temp.scrape_option.get("video")

        self.add_date_source_box.init_data(option)

    def save(self):
        return {
            "video": {
                **self.add_date_source_box.save()
            }
        }
