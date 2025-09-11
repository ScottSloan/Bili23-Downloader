import wx

from utils.config import Config
from utils.common.style.color import Color

from gui.dialog.setting.ass_style.page import Page

from gui.component.staticbox.font import FontStaticBox
from gui.component.staticbox.border import BorderStaticBox
from gui.component.staticbox.misc_style import MiscStyleStaticBox
from gui.component.misc.ass_color_picker import ASSColorPicker
from gui.component.spinctrl.label_spinctrl import LabelSpinCtrl
from gui.component.panel.panel import Panel

class ColorStaticBox(Panel):
    def __init__(self, parent: wx.Window):
        Panel.__init__(self, parent)

        self.init_UI()

    def init_UI(self):
        color_box = wx.StaticBox(self, -1, "颜色")

        self.primary_color_picker = ASSColorPicker(color_box, "主要颜色", wx.HORIZONTAL)
        self.secondary_color_picker = ASSColorPicker(color_box, "次要颜色", wx.HORIZONTAL)
        self.border_color_picker = ASSColorPicker(color_box, "边框颜色", wx.HORIZONTAL)
        self.shadow_color_picker = ASSColorPicker(color_box, "阴影颜色", wx.HORIZONTAL)

        flex_grid_box = wx.FlexGridSizer(2, 2, 0, 0)
        flex_grid_box.Add(self.primary_color_picker, 0, wx.ALIGN_RIGHT)
        flex_grid_box.Add(self.secondary_color_picker, 0, wx.ALIGN_RIGHT)
        flex_grid_box.Add(self.border_color_picker, 0, wx.ALIGN_RIGHT)
        flex_grid_box.Add(self.shadow_color_picker, 0, wx.ALIGN_RIGHT)

        color_sbox = wx.StaticBoxSizer(color_box, wx.HORIZONTAL)
        color_sbox.Add(flex_grid_box, 0, wx.EXPAND)

        self.SetSizer(color_sbox)

    def init_data(self, style: dict):
        self.primary_color_picker.SetColour(style.get("primary_color"))
        self.secondary_color_picker.SetColour(style.get("secondary_color"))
        self.border_color_picker.SetColour(style.get("border_color"))
        self.shadow_color_picker.SetColour(style.get("shadow_color"))

    def get_option(self):
        return {
            "primary_color": self.get_ass_style_color(self.primary_color_picker),
            "secondary_color": self.get_ass_style_color(self.secondary_color_picker),
            "border_color": self.get_ass_style_color(self.border_color_picker),
            "shadow_color": self.get_ass_style_color(self.shadow_color_picker),
        }

    def get_ass_style_color(self, window: wx.Window):
        color: wx.Colour = window.GetColour()
        return Color.convert_to_ass_abgr_color(color.GetAsString(wx.C2S_HTML_SYNTAX))

class MarginStaticBox(Panel):
    def __init__(self, parent: wx.Window):
        Panel.__init__(self, parent)

        self.init_UI()

    def init_UI(self):
        margin_box = wx.StaticBox(self, -1, "边距")

        self.left_margin_box = LabelSpinCtrl(margin_box, "左边距", 10, "px", wx.HORIZONTAL)
        self.left_margin_box.SetToolTip("与画面左边界的距离")
        self.right_margin_box = LabelSpinCtrl(margin_box, "右边距", 10, "px", wx.HORIZONTAL)
        self.right_margin_box.SetToolTip("与画面右边界的距离")
        self.vertical_margin_box = LabelSpinCtrl(margin_box, "垂直边距", 10, "px", wx.HORIZONTAL)
        self.vertical_margin_box.SetToolTip("与画面上/下边界的距离")

        flex_grid_box = wx.FlexGridSizer(2, 3, 0, 0)
        flex_grid_box.Add(self.left_margin_box, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM) | wx.ALIGN_RIGHT, self.FromDIP(6))
        flex_grid_box.AddSpacer(self.FromDIP(10))
        flex_grid_box.Add(self.right_margin_box, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM) | wx.ALIGN_RIGHT, self.FromDIP(6))
        flex_grid_box.Add(self.vertical_margin_box, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM) | wx.ALIGN_RIGHT, self.FromDIP(6))
        flex_grid_box.AddSpacer(self.FromDIP(10))
        flex_grid_box.AddSpacer(1)

        margin_sbox = wx.StaticBoxSizer(margin_box, wx.VERTICAL)
        margin_sbox.Add(flex_grid_box, 0, wx.EXPAND)

        self.SetSizer(margin_sbox)

    def init_data(self, style: dict):
        self.left_margin_box.SetValue(style.get("marginL"))
        self.right_margin_box.SetValue(style.get("marginR"))
        self.vertical_margin_box.SetValue(style.get("marginV"))

    def get_option(self):
        return {
            "marginL": self.left_margin_box.GetValue(),
            "marginR": self.right_margin_box.GetValue(),
            "marginV": self.vertical_margin_box.GetValue()
        }

class SubtitlePage(Page):
    def __init__(self, parent: wx.Window):
        Page.__init__(self, parent)

        self.init_UI()

        self.init_data()

    def init_UI(self):
        self.font_sbox = FontStaticBox(self.panel)
        self.border_sbox = BorderStaticBox(self.panel)
        self.color_sbox = ColorStaticBox(self.panel)
        self.misc_sbox = MiscStyleStaticBox(self.panel)
        self.margin_sbox = MarginStaticBox(self.panel)

        self.align_radio_box = wx.RadioBox(self.panel, -1, "对齐方式", choices = ["7", "8", "9", "4", "5", "6", "1", "2", "3"], majorDimension = 3)
        self.align_radio_box.SetToolTip("字幕在画面中位置的对齐方式，按照小键盘区布局")

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.font_sbox, 0, wx.ALL | wx.EXPAND, self.FromDIP(6))
        vbox.Add(self.border_sbox, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))
        vbox.Add(self.color_sbox, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))
        vbox.Add(self.misc_sbox, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))
        vbox.Add(self.margin_sbox, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))
        vbox.Add(self.align_radio_box, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))

        self.panel.SetSizer(vbox)

        super().init_UI()

    def init_data(self):
        subtitle_style = Config.Temp.ass_style.get("subtitle")

        self.font_sbox.init_data(subtitle_style)
        self.border_sbox.init_data(subtitle_style)
        self.misc_sbox.init_data(subtitle_style)
        self.color_sbox.init_data(subtitle_style)
        self.margin_sbox.init_data(subtitle_style)
        self.align_radio_box.SetStringSelection(str(subtitle_style.get("alignment")))

    def get_option(self):
        font_option = self.font_sbox.get_option()
        border_option = self.border_sbox.get_option()
        misc_option = self.misc_sbox.get_option()
        color_option = self.color_sbox.get_option()
        margin_option = self.margin_sbox.get_option()

        return "subtitle", {
            **font_option,
            **border_option,
            **misc_option,
            **color_option,
            **margin_option,
            "alignment": int(self.align_radio_box.GetStringSelection())
        }
