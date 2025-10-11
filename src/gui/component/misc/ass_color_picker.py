import wx

from utils.common.style.color import Color

from gui.dialog.setting.color_picker import ColorPickerDialog

from gui.component.panel.panel import Panel

class ASSColorPicker(Panel):
    def __init__(self, parent, label: str, orient: int):
        self.label = label

        Panel.__init__(self, parent)

        match orient:
            case wx.HORIZONTAL:
                self.init_horizontal_UI()

            case wx.VERTICAL:
                self.init_vertical_UI()

        self.Bind_EVT()

    def init_vertical_UI(self):
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

    def init_horizontal_UI(self):
        self.text_lab = wx.StaticText(self, -1, self.label)

        self.color_picker = wx.ColourPickerCtrl(self, -1, style = wx.CLRP_SHOW_ALPHA)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.text_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        hbox.Add(self.color_picker, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.SetSizer(hbox)

    def Bind_EVT(self):
        self.color_picker.Bind(wx.EVT_BUTTON, self.onColorChangeEVT)

    def onColorChangeEVT(self, event: wx.ColourPickerEvent):
        dlg = ColorPickerDialog(self)
        dlg.ShowModal()

    def SetColour(self, color_str: str):
        r, g, b, a = Color.convert_to_abgr_color(color_str)

        color = wx.Colour(r, g, b)
        self.color_picker.SetColour(color)

    def GetColour(self):
        return self.color_picker.GetColour()