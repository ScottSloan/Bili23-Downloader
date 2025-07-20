import wx

from utils.config import Config

from utils.common.color import Color

from gui.component.window.dialog import Dialog
from gui.component.panel.panel import Panel

from gui.component.misc.ass_color_picker import ASSColorPicker
from gui.component.misc.label_spinctrl import LabelSpinCtrl
from gui.component.staticbox.font import FontStaticBox
from gui.component.staticbox.border import BorderStaticBox

class DanmakuPage(Panel):
    def __init__(self, parent):
        Panel.__init__(self, parent)

        self.init_UI()

        self.init_data()

    def init_UI(self):
        self.font_sbox = FontStaticBox(self)

        self.border_sbox = BorderStaticBox(self)

        misc_box = wx.StaticBox(self, -1, "杂项")

        scroll_duration_lab = wx.StaticText(misc_box, -1, "普通弹幕滚动时长")
        self.scroll_duration_box = wx.SpinCtrl(misc_box, -1, min = 1, max = 15, initial = 0)
        scroll_duration_unit_lab = wx.StaticText(misc_box, -1, "s")

        scroll_duration_hbox = wx.BoxSizer(wx.HORIZONTAL)
        scroll_duration_hbox.Add(self.scroll_duration_box, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))
        scroll_duration_hbox.Add(scroll_duration_unit_lab, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        stay_duration_lab = wx.StaticText(misc_box, -1, "顶部/底部弹幕停留时长")
        self.stay_duration_box = wx.SpinCtrl(misc_box, -1, min = 1, max = 30, initial = 0)
        stay_duration_unit_lab = wx.StaticText(misc_box, -1, "s")

        stay_duration_hbox = wx.BoxSizer(wx.HORIZONTAL)
        stay_duration_hbox.Add(self.stay_duration_box, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))
        stay_duration_hbox.Add(stay_duration_unit_lab, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        misc_grid_box = wx.FlexGridSizer(2, 2, 0, 0)
        misc_grid_box.Add(scroll_duration_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        misc_grid_box.Add(scroll_duration_hbox, 0, wx.EXPAND)
        misc_grid_box.Add(stay_duration_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        misc_grid_box.Add(stay_duration_hbox, 0, wx.EXPAND)

        misc_sbox = wx.StaticBoxSizer(misc_box, wx.VERTICAL)
        misc_sbox.Add(misc_grid_box, 0, wx.EXPAND)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.font_sbox, 0, wx.ALL | wx.EXPAND, self.FromDIP(6))
        vbox.Add(self.border_sbox, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))
        vbox.Add(misc_sbox, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))

        self.SetSizer(vbox)

    def init_data(self):
        danmaku = Config.Temp.ass_style.get("danmaku")

        self.font_sbox.init_data(danmaku)
        self.border_sbox.init_data(danmaku)

        self.scroll_duration_box.SetValue(danmaku.get("scroll_duration"))
        self.stay_duration_box.SetValue(danmaku.get("stay_duration"))
    
    def get_option(self):
        font_option = self.font_sbox.get_option()
        border_option = self.border_sbox.get_option()

        return "danmaku", {
            **font_option,
            **border_option,
            "scroll_duration": self.scroll_duration_box.GetValue(),
            "stay_duration": self.stay_duration_box.GetValue()
        }

class SubtitlePage(Panel):
    def __init__(self, parent):
        Panel.__init__(self, parent)

        self.init_UI()

        self.init_data()

    def init_UI(self):
        self.font_sbox = FontStaticBox(self)

        self.border_sbox = BorderStaticBox(self)

        color_box = wx.StaticBox(self, -1, "颜色")
        
        self.primary_color_picker = ASSColorPicker(self, "主要颜色")
        self.border_color_picker = ASSColorPicker(self, "边框")
        self.shadow_color_picker = ASSColorPicker(self, "阴影")

        color_sbox = wx.StaticBoxSizer(color_box, wx.HORIZONTAL)
        color_sbox.Add(self.primary_color_picker, 0, wx.EXPAND)
        color_sbox.Add(self.border_color_picker, 0, wx.EXPAND)
        color_sbox.Add(self.shadow_color_picker, 0, wx.EXPAND)

        margin_box = wx.StaticBox(self, -1, "边距")

        self.left_margin_box = LabelSpinCtrl(self, "左边距", 10, "px", wx.VERTICAL)
        self.left_margin_box.SetToolTip("与画面左边界的距离")
        self.right_margin_box = LabelSpinCtrl(self, "右边距", 10, "px", wx.VERTICAL)
        self.right_margin_box.SetToolTip("与画面右边界的距离")
        self.vertical_margin_box = LabelSpinCtrl(self, "垂直边距", 10, "px", wx.VERTICAL)
        self.vertical_margin_box.SetToolTip("与画面上/下边界的距离")

        margin_sbox = wx.StaticBoxSizer(margin_box, wx.HORIZONTAL)
        margin_sbox.Add(self.left_margin_box, 0, wx.ALL, self.FromDIP(6))
        margin_sbox.Add(self.right_margin_box, 0, wx.ALL, self.FromDIP(6))
        margin_sbox.Add(self.vertical_margin_box, 0, wx.ALL, self.FromDIP(6))

        self.align_radio_box = wx.RadioBox(self, -1, "对齐方式", choices = ["7", "8", "9", "4", "5", "6", "1", "2", "3"], majorDimension = 3)
        self.align_radio_box.SetToolTip("字幕在画面中位置的对齐方式，按照小键盘区布局")

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(margin_sbox, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))
        hbox.Add(self.align_radio_box, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.font_sbox, 0, wx.ALL | wx.EXPAND, self.FromDIP(6))
        vbox.Add(self.border_sbox, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))
        vbox.Add(color_sbox, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))
        vbox.Add(hbox, 0, wx.EXPAND)

        self.SetSizer(vbox)

    def init_data(self):
        subtitle = Config.Temp.ass_style.get("subtitle")

        self.font_sbox.init_data(subtitle)
        self.border_sbox.init_data(subtitle)

        self.primary_color_picker.SetColour(subtitle.get("primary_color"))
        self.border_color_picker.SetColour(subtitle.get("border_color"))
        self.shadow_color_picker.SetColour(subtitle.get("shadow_color"))

        self.left_margin_box.SetValue(subtitle.get("marginL"))
        self.right_margin_box.SetValue(subtitle.get("marginR"))
        self.vertical_margin_box.SetValue(subtitle.get("marginV"))

        self.align_radio_box.SetStringSelection(str(subtitle.get("alignment")))

    def get_option(self):
        def get_ass_style_color(window: wx.Window):
            color: wx.Colour = window.GetColour()
            return Color.convert_to_ass_style_color(color.GetAsString(wx.C2S_HTML_SYNTAX))

        font_option = self.font_sbox.get_option()
        border_option = self.border_sbox.get_option()

        return "subtitle", {
            **font_option,
            **border_option,
            "primary_color": get_ass_style_color(self.primary_color_picker),
            "border_color": get_ass_style_color(self.border_color_picker),
            "shadow_color": get_ass_style_color(self.shadow_color_picker),
            "marginL": self.left_margin_box.GetValue(),
            "marginR": self.right_margin_box.GetValue(),
            "marginV": self.vertical_margin_box.GetValue(),
            "alignment": int(self.align_radio_box.GetStringSelection())
        }

class CustomASSStyleDialog(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent, "自定义 ASS 样式")

        self.init_UI()

        self.CenterOnParent()

    def init_UI(self):
        self.notebook = wx.Notebook(self, -1)

        self.notebook.AddPage(DanmakuPage(self.notebook), "弹幕")
        self.notebook.AddPage(SubtitlePage(self.notebook), "字幕")

        self.ok_btn = wx.Button(self, wx.ID_OK, "确定", size = self.get_scaled_size((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, "取消", size = self.get_scaled_size((80, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer(1)
        bottom_hbox.Add(self.ok_btn, 0, wx.ALL, self.FromDIP(6))
        bottom_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.notebook, 0, wx.ALL & (~wx.BOTTOM) | wx.EXPAND, self.FromDIP(6))
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def onOKEVT(self):
        for i in range(self.notebook.GetPageCount()):
            page, option = self.notebook.GetPage(i).get_option()

            Config.Temp.ass_style[page] = option
