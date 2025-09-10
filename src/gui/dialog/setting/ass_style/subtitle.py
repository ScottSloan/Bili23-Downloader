import wx

from utils.config import Config
from utils.common.style.color import Color

from gui.dialog.setting.ass_style.page import Page

from gui.component.staticbox.font import FontStaticBox
from gui.component.staticbox.border import BorderStaticBox
from gui.component.staticbox.misc_style import MiscStyleStaticBox
from gui.component.misc.ass_color_picker import ASSColorPicker
from gui.component.spinctrl.label_spinctrl import LabelSpinCtrl

class SubtitlePage(Page):
    def __init__(self, parent: wx.Window):
        Page.__init__(self, parent)

        self.init_UI()

        self.init_data()

    def init_UI(self):
        self.font_sbox = FontStaticBox(self.panel)
        self.border_sbox = BorderStaticBox(self.panel)

        color_box = wx.StaticBox(self.panel, -1, "颜色")

        self.primary_color_picker = ASSColorPicker(self.panel, "主要颜色")
        self.border_color_picker = ASSColorPicker(self.panel, "边框")
        self.shadow_color_picker = ASSColorPicker(self.panel, "阴影")

        color_sbox = wx.StaticBoxSizer(color_box, wx.HORIZONTAL)
        color_sbox.Add(self.primary_color_picker, 0, wx.EXPAND)
        color_sbox.Add(self.border_color_picker, 0, wx.EXPAND)
        color_sbox.Add(self.shadow_color_picker, 0, wx.EXPAND)

        self.misc_sbox = MiscStyleStaticBox(self.panel)

        margin_box = wx.StaticBox(self.panel, -1, "边距")

        self.left_margin_box = LabelSpinCtrl(margin_box, "左边距", 10, "px", wx.VERTICAL)
        self.left_margin_box.SetToolTip("与画面左边界的距离")
        self.right_margin_box = LabelSpinCtrl(margin_box, "右边距", 10, "px", wx.VERTICAL)
        self.right_margin_box.SetToolTip("与画面右边界的距离")
        self.vertical_margin_box = LabelSpinCtrl(margin_box, "垂直边距", 10, "px", wx.VERTICAL)
        self.vertical_margin_box.SetToolTip("与画面上/下边界的距离")

        margin_sbox = wx.StaticBoxSizer(margin_box, wx.HORIZONTAL)
        margin_sbox.Add(self.left_margin_box, 0, wx.ALL, self.FromDIP(6))
        margin_sbox.Add(self.right_margin_box, 0, wx.ALL, self.FromDIP(6))
        margin_sbox.Add(self.vertical_margin_box, 0, wx.ALL, self.FromDIP(6))

        self.align_radio_box = wx.RadioBox(self.panel, -1, "对齐方式", choices = ["7", "8", "9", "4", "5", "6", "1", "2", "3"], majorDimension = 3)
        self.align_radio_box.SetToolTip("字幕在画面中位置的对齐方式，按照小键盘区布局")

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(margin_sbox, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))
        hbox.Add(self.align_radio_box, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.font_sbox, 0, wx.ALL | wx.EXPAND, self.FromDIP(6))
        vbox.Add(self.border_sbox, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))
        vbox.Add(color_sbox, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))
        vbox.Add(self.misc_sbox, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))
        vbox.Add(hbox, 0, wx.EXPAND)

        self.panel.SetSizer(vbox)

        super().init_UI()

    def init_data(self):
        subtitle = Config.Temp.ass_style.get("subtitle")

        self.font_sbox.init_data(subtitle)
        self.border_sbox.init_data(subtitle)
        self.misc_sbox.init_data(subtitle)

        self.primary_color_picker.SetColour(subtitle.get("primary_color"))
        self.border_color_picker.SetColour(subtitle.get("border_color"))
        self.shadow_color_picker.SetColour(subtitle.get("shadow_color"))

        self.left_margin_box.SetValue(subtitle.get("marginL"))
        self.right_margin_box.SetValue(subtitle.get("marginR"))
        self.vertical_margin_box.SetValue(subtitle.get("marginV"))

        self.align_radio_box.SetStringSelection(str(subtitle.get("alignment")))

    def get_option(self):
        font_option = self.font_sbox.get_option()
        border_option = self.border_sbox.get_option()
        misc_option = self.misc_sbox.get_option()

        return "subtitle", {
            **font_option,
            **border_option,
            **misc_option,
            "primary_color": self.get_ass_style_color(self.primary_color_picker),
            "border_color": self.get_ass_style_color(self.border_color_picker),
            "shadow_color": self.get_ass_style_color(self.shadow_color_picker),
            "marginL": self.left_margin_box.GetValue(),
            "marginR": self.right_margin_box.GetValue(),
            "marginV": self.vertical_margin_box.GetValue(),
            "alignment": int(self.align_radio_box.GetStringSelection())
        }
    
    def get_ass_style_color(window: wx.Window):
        color: wx.Colour = window.GetColour()
        return Color.convert_to_ass_abgr_color(color.GetAsString(wx.C2S_HTML_SYNTAX))

