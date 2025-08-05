import wx

from utils.common.style.color import Color

from gui.component.panel.panel import Panel

class ASSColorPicker(Panel):
    def __init__(self, parent, label: str):
        self.label = label

        Panel.__init__(self, parent)

        self.init_UI()

    def init_UI(self):
        self.text_lab = wx.StaticText(self, -1, self.label)

        lab_hbox = wx.BoxSizer(wx.HORIZONTAL)
        lab_hbox.AddStretchSpacer()
        lab_hbox.Add(self.text_lab, 0, wx.ALL, self.FromDIP(6))
        lab_hbox.AddStretchSpacer()

        self.color_picker = wx.ColourPickerCtrl(self, -1, style = wx.CLRP_SHOW_ALPHA)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(lab_hbox, 0, wx.EXPAND)
        vbox.Add(self.color_picker, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))

        self.SetSizer(vbox)

    def SetColour(self, color_str: str):
        color = wx.Colour()
        color.SetRGBA(Color.convert_to_abgr_color(color_str))

        self.color_picker.SetColour(color)

    def GetColour(self):
        return self.color_picker.GetColour()