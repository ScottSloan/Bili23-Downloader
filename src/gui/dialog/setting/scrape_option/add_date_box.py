import wx

from utils.common.map import nfo_add_date_map

from gui.component.panel.panel import Panel
from gui.component.choice.choice import Choice

class AddDateBox(Panel):
    def __init__(self, parent: wx.Window):
        Panel.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

    def init_UI(self):
        self.add_date_chk = wx.CheckBox(self, -1, "将 <添加日期> 添加到 NFO")
        self.add_date_source_lab = wx.StaticText(self, -1, "<添加日期> 来源")
        self.add_date_source_choice = Choice(self)
        self.add_date_source_choice.SetChoices(nfo_add_date_map)

        add_source_hbox = wx.BoxSizer(wx.HORIZONTAL)
        add_source_hbox.AddSpacer(self.FromDIP(20))
        add_source_hbox.Add(self.add_date_source_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        add_source_hbox.Add(self.add_date_source_choice, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        add_source_vbox = wx.BoxSizer(wx.VERTICAL)
        add_source_vbox.Add(self.add_date_chk, 0, wx.ALL & (~wx.BOTTOM), self.FromDIP(6))
        add_source_vbox.Add(add_source_hbox, 0, wx.EXPAND)

        self.SetSizer(add_source_vbox)

    def Bind_EVT(self):
        self.add_date_chk.Bind(wx.EVT_CHECKBOX, self.onAddDateEVT)

    def init_data(self, option: dict):
        self.add_date_chk.SetValue(option.get("add_date", True))
        self.add_date_source_choice.SetSelection(option.get("add_date_source", 0))

        self.onAddDateEVT(0)

    def save(self):
        return {
            "add_date": self.add_date_chk.GetValue(),
            "add_date_source": self.add_date_source_choice.GetSelection()
        }
    
    def onAddDateEVT(self, event: wx.CommandEvent):
        enable = self.add_date_chk.GetValue()

        self.add_date_source_lab.Enable(enable)
        self.add_date_source_choice.Enable(enable)

