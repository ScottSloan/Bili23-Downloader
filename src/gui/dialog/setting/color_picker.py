import wx

from gui.component.window.dialog import Dialog
from gui.component.panel.panel import Panel
from gui.component.spinctrl.label_spinctrl import LabelSpinCtrl

class RGBStaticBox(Panel):
    def __init__(self, parent: wx.Window):
        Panel.__init__(self, parent)

        self.init_UI()

    def init_UI(self):
        rgb_box = wx.StaticBox(self, -1, "RGB 颜色")

        self.r_spinctrl = LabelSpinCtrl(rgb_box, "R", value = 0, unit = "", min = 0, max = 255)
        self.g_spinctrl = LabelSpinCtrl(rgb_box, "G", value = 0, unit = "", min = 0, max = 255)
        self.b_spinctrl = LabelSpinCtrl(rgb_box, "B", value = 0, unit = "", min = 0, max = 255)

        flex_grid_box = wx.FlexGridSizer(1, 3, 0, 0)
        flex_grid_box.Add(self.r_spinctrl, 0, wx.ALIGN_RIGHT)
        flex_grid_box.Add(self.g_spinctrl, 0, wx.ALIGN_RIGHT)
        flex_grid_box.Add(self.b_spinctrl, 0, wx.ALIGN_RIGHT)

        rgb_sbox = wx.StaticBoxSizer(rgb_box, wx.VERTICAL)
        rgb_sbox.Add(flex_grid_box, 0, wx.EXPAND)

        self.SetSizer(rgb_sbox)

class ColorPickerDialog(Dialog):
    def __init__(self, parent: wx.Window):
        Dialog.__init__(self, parent, "选择颜色")

        self.init_UI()

        self.CenterOnParent()

    def init_UI(self):
        self.rgb_sbox = RGBStaticBox(self)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.rgb_sbox, 0, wx.ALL | wx.EXPAND, self.FromDIP(6))

        self.SetSizerAndFit(vbox)