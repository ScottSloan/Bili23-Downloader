import wx

from utils.common.color import Color

from gui.component.panel.panel import Panel

class ASSColorPicker(Panel):
    def __init__(self, parent, label: str):
        self.label = label

        Panel.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

    def init_UI(self):
        self.text_lab = wx.StaticText(self, -1, self.label)
        self.color_picker = wx.ColourPickerCtrl(self, -1, style = wx.CLRP_SHOW_ALPHA)

        self.color_lab = wx.StaticText(self, -1)

        color_hbox = wx.BoxSizer(wx.HORIZONTAL)
        color_hbox.AddStretchSpacer()
        color_hbox.Add(self.color_lab, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        color_hbox.AddStretchSpacer()

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.text_lab, 0, wx.ALL, self.FromDIP(6))
        vbox.Add(self.color_picker, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        vbox.Add(color_hbox, 0, wx.EXPAND)

        self.SetSizer(vbox)

    def Bind_EVT(self):
        self.color_picker.Bind(wx.EVT_COLOURPICKER_CHANGED, self.onChangeColour)

    def SetColour(self, color_str: str):
        color = wx.Colour()
        color.SetRGBA(Color.convert_to_abgr_color(color_str))

        self.color_picker.SetColour(color)
        self.color_lab.SetLabel(color_str)

    def GetColour(self):
        return self.color_picker.GetColour()
    
    def onChangeColour(self, event):
        color: wx.Colour = self.color_picker.GetColour()

        self.color_lab.SetLabel(Color.convert_to_ass_style_color(color.GetAsString(wx.C2S_HTML_SYNTAX)))