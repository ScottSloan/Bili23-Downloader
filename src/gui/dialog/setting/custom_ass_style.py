import wx

from utils.config import Config

from utils.common.style.color import Color

from gui.component.window.dialog import Dialog
from gui.component.panel.panel import Panel

from gui.component.misc.ass_color_picker import ASSColorPicker
from gui.component.spinctrl.label_spinctrl import LabelSpinCtrl
from gui.component.staticbox.font import FontStaticBox
from gui.component.staticbox.border import BorderStaticBox
from gui.component.staticbox.misc_style import MiscStyleStaticBox

class DanmakuPage(Panel):
    def __init__(self, parent):
        Panel.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

        self.init_data()

    def init_UI(self):
        self.font_sbox = FontStaticBox(self)

        self.border_sbox = BorderStaticBox(self)

        self.misc_sbox = MiscStyleStaticBox(self)

        misc_box = wx.StaticBox(self, -1, "高级设置")

        self.subtitle_obstruct_chk = wx.CheckBox(misc_box, -1, "防遮挡字幕")

        alpha_lab = wx.StaticText(misc_box, -1, "不透明度")
        self.alpha_slider = wx.Slider(misc_box, -1, value = 80, minValue = 10, maxValue = 100)
        self.alpha_indicator_lab = wx.StaticText(misc_box, -1, "80%")

        alpha_hbox = wx.BoxSizer(wx.HORIZONTAL)
        alpha_hbox.Add(alpha_lab, 0, wx.ALL & (~wx.BOTTOM) | wx.ALIGN_CENTER, self.FromDIP(6))
        alpha_hbox.Add(self.alpha_slider, 1, wx.ALL & (~wx.LEFT) & (~wx.BOTTOM)| wx.EXPAND, self.FromDIP(6))
        alpha_hbox.Add(self.alpha_indicator_lab, 0, wx.ALL & (~wx.LEFT) & (~wx.BOTTOM) | wx.ALIGN_CENTER, self.FromDIP(6))

        danmaku_speed_lab = wx.StaticText(misc_box, -1, "弹幕速度")
        self.danmaku_speed_slider = wx.Slider(misc_box, -1, value = 3, minValue = 1, maxValue = 5)
        self.danmaku_speed_indicator_lab = wx.StaticText(misc_box, -1, "适中")

        danmaku_speed_hbox = wx.BoxSizer(wx.HORIZONTAL)
        danmaku_speed_hbox.Add(danmaku_speed_lab, 0, wx.ALL & (~wx.BOTTOM) | wx.ALIGN_CENTER, self.FromDIP(6))
        danmaku_speed_hbox.Add(self.danmaku_speed_slider, 1, wx.ALL & (~wx.LEFT) & (~wx.BOTTOM) | wx.EXPAND, self.FromDIP(6))
        danmaku_speed_hbox.Add(self.danmaku_speed_indicator_lab, 0, wx.ALL & (~wx.LEFT) & (~wx.BOTTOM) | wx.ALIGN_CENTER, self.FromDIP(6))

        danmaku_density_lab = wx.StaticText(misc_box, -1, "弹幕密度")
        self.danmaku_density_slider = wx.Slider(misc_box, -1, value = 2, minValue = 1, maxValue = 3)
        self.danmaku_density_indicator_lab = wx.StaticText(misc_box, -1, "较多")

        danmaku_density_hbox = wx.BoxSizer(wx.HORIZONTAL)
        danmaku_density_hbox.Add(danmaku_density_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        danmaku_density_hbox.Add(self.danmaku_density_slider, 1, wx.ALL & (~wx.LEFT) | wx.EXPAND, self.FromDIP(6))
        danmaku_density_hbox.Add(self.danmaku_density_indicator_lab, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        
        misc_sbox = wx.StaticBoxSizer(misc_box, wx.VERTICAL)
        misc_sbox.Add(self.subtitle_obstruct_chk, 0, wx.ALL & (~wx.BOTTOM), self.FromDIP(6))
        misc_sbox.Add(alpha_hbox, 0, wx.EXPAND)
        misc_sbox.Add(danmaku_speed_hbox, 0, wx.EXPAND)
        misc_sbox.Add(danmaku_density_hbox, 0, wx.EXPAND)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.font_sbox, 0, wx.ALL | wx.EXPAND, self.FromDIP(6))
        vbox.Add(self.border_sbox, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))
        vbox.Add(self.misc_sbox, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))
        vbox.Add(misc_sbox, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))

        self.SetSizer(vbox)

    def Bind_EVT(self):
        self.alpha_slider.Bind(wx.EVT_SLIDER, self.onAlphaSliderEVT)
        self.danmaku_speed_slider.Bind(wx.EVT_SLIDER, self.onDanmakuSpeedSliderEVT)
        self.danmaku_density_slider.Bind(wx.EVT_SLIDER, self.onDanmakuDensitySliderEVT)

    def init_data(self):
        danmaku_style = Config.Temp.ass_style.get("danmaku")

        self.font_sbox.init_data(danmaku_style)
        self.border_sbox.init_data(danmaku_style)
        self.misc_sbox.init_data(danmaku_style)

        self.subtitle_obstruct_chk.SetValue(danmaku_style.get("subtitle_obstruct", False))
        self.alpha_slider.SetValue(danmaku_style.get("alpha", 80))
        self.danmaku_speed_slider.SetValue(danmaku_style.get("speed", 3))
        self.danmaku_density_slider.SetValue(danmaku_style.get("density", 1))

        self.onAlphaSliderEVT(0)
        self.onDanmakuSpeedSliderEVT(0)
        self.onDanmakuDensitySliderEVT(0)

    def get_option(self):
        font_option = self.font_sbox.get_option()
        border_option = self.border_sbox.get_option()
        misc_option = self.misc_sbox.get_option()

        return "danmaku", {
            **font_option,
            **border_option,
            **misc_option,
            "subtitle_obstruct": self.subtitle_obstruct_chk.GetValue(),
            "alpha": self.alpha_slider.GetValue(),
            "speed": self.danmaku_speed_slider.GetValue(),
            "density": self.danmaku_density_slider.GetValue()
        }

    def onAlphaSliderEVT(self, event):
        self.alpha_indicator_lab.SetLabel(f"{self.alpha_slider.GetValue()}%")

    def onDanmakuSpeedSliderEVT(self, event):
        match self.danmaku_speed_slider.GetValue():
            case 1:
                self.danmaku_speed_indicator_lab.SetLabel("极慢")
            case 2:
                self.danmaku_speed_indicator_lab.SetLabel("较慢")
            case 3:
                self.danmaku_speed_indicator_lab.SetLabel("适中")
            case 4:
                self.danmaku_speed_indicator_lab.SetLabel("较快")
            case 5:
                self.danmaku_speed_indicator_lab.SetLabel("极快")

    def onDanmakuDensitySliderEVT(self, event):
        match self.danmaku_density_slider.GetValue():
            case 1:
                self.danmaku_density_indicator_lab.SetLabel("正常")
            case 2:
                self.danmaku_density_indicator_lab.SetLabel("较多")
            case 3:
                self.danmaku_density_indicator_lab.SetLabel("重叠")

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

        self.misc_sbox = MiscStyleStaticBox(self)

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
        vbox.Add(self.misc_sbox, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))
        vbox.Add(hbox, 0, wx.EXPAND)

        self.SetSizer(vbox)

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
        def get_ass_style_color(window: wx.Window):
            color: wx.Colour = window.GetColour()
            return Color.convert_to_ass_abgr_color(color.GetAsString(wx.C2S_HTML_SYNTAX))

        font_option = self.font_sbox.get_option()
        border_option = self.border_sbox.get_option()
        misc_option = self.misc_sbox.get_option()

        return "subtitle", {
            **font_option,
            **border_option,
            **misc_option,
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
