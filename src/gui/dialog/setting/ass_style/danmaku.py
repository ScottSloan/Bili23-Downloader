import wx

from utils.config import Config
from utils.common.data.danmaku_ass_style import area_data, alpha_data, speed_data, density_data

from gui.dialog.setting.ass_style.page import Page

from gui.component.staticbox.font import FontStaticBox
from gui.component.staticbox.border import BorderStaticBox
from gui.component.staticbox.misc_style import MiscStyleStaticBox
from gui.component.slider.label_slider import LabelSlider

class DanmakuPage(Page):
    def __init__(self, parent: wx.Window):
        Page.__init__(self, parent)

        self.init_UI()

        self.init_data()

    def init_UI(self):
        self.font_sbox = FontStaticBox(self.panel)
        self.border_sbox = BorderStaticBox(self.panel)
        self.misc_sbox = MiscStyleStaticBox(self.panel)

        misc_box = wx.StaticBox(self.panel, -1, "高级设置")

        self.subtitle_obstruct_chk = wx.CheckBox(misc_box, -1, "防遮挡字幕")

        self.danmaku_area_slider = LabelSlider(misc_box, area_data)
        self.danmaku_alpha_slider = LabelSlider(misc_box, alpha_data)
        self.danmaku_speed_slider = LabelSlider(misc_box, speed_data)
        self.danmaku_density_slider = LabelSlider(misc_box, density_data)

        misc_sbox = wx.StaticBoxSizer(misc_box, wx.VERTICAL)
        misc_sbox.Add(self.subtitle_obstruct_chk, 0, wx.ALL & (~wx.BOTTOM), self.FromDIP(6))
        misc_sbox.Add(self.danmaku_area_slider, 0, wx.EXPAND)
        misc_sbox.Add(self.danmaku_alpha_slider, 0, wx.EXPAND)
        misc_sbox.Add(self.danmaku_speed_slider, 0, wx.EXPAND)
        misc_sbox.Add(self.danmaku_density_slider, 0, wx.EXPAND)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.font_sbox, 0, wx.ALL | wx.EXPAND, self.FromDIP(6))
        vbox.Add(self.border_sbox, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))
        vbox.Add(self.misc_sbox, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))
        vbox.Add(misc_sbox, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))

        self.panel.SetSizer(vbox)

        super().init_UI()

    def init_data(self):
        danmaku_style = Config.Temp.ass_style.get("danmaku")

        self.font_sbox.init_data(danmaku_style)
        self.border_sbox.init_data(danmaku_style)
        self.misc_sbox.init_data(danmaku_style)

        self.subtitle_obstruct_chk.SetValue(danmaku_style.get("subtitle_obstruct", False))
        self.danmaku_area_slider.SetValue(danmaku_style.get("area", 5))
        self.danmaku_alpha_slider.SetValue(danmaku_style.get("alpha", 80))
        self.danmaku_speed_slider.SetValue(danmaku_style.get("speed", 3))
        self.danmaku_density_slider.SetValue(danmaku_style.get("density", 1))

    def get_option(self):
        font_option = self.font_sbox.get_option()
        border_option = self.border_sbox.get_option()
        misc_option = self.misc_sbox.get_option()

        return "danmaku", {
            **font_option,
            **border_option,
            **misc_option,
            "subtitle_obstruct": self.subtitle_obstruct_chk.GetValue(),
            "area": self.danmaku_area_slider.GetValue(),
            "alpha": self.danmaku_alpha_slider.GetValue(),
            "speed": self.danmaku_speed_slider.GetValue(),
            "density": self.danmaku_density_slider.GetValue()
        }