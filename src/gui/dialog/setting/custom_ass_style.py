import wx

from utils.config import Config

from utils.common.map import resolution_map
from utils.common.color import Color

from gui.component.window.dialog import Dialog
from gui.component.panel.panel import Panel

from gui.component.tooltip import ToolTip
from gui.component.ass_color_picker import ASSColorPicker
from gui.component.label_spinctrl import LabelSpinCtrl

class DanmakuPage(Panel):
    def __init__(self, parent):
        Panel.__init__(self, parent)

        self.height = 1080

        self.init_UI()

        self.Bind_EVT()

        self.init_data()

    def init_UI(self):
        font_name_lab = wx.StaticText(self, -1, "字体名称")
        self.font_name_preview_lab = wx.StaticText(self, -1, self.GetFont().GetFaceName())
        self.font_name_btn = wx.Button(self, -1, "更改", size = self.get_scaled_size((50, 24)))

        font_name_hbox = wx.BoxSizer(wx.HORIZONTAL)
        font_name_hbox.Add(self.font_name_preview_lab, 0, wx.ALL| wx.ALIGN_CENTER, self.FromDIP(6))
        font_name_hbox.Add(self.font_name_btn, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))

        font_size_lab = wx.StaticText(self, -1, "字体大小")
        self.font_size_box = wx.SpinCtrl(self, -1, min = 1, max = 100, initial = 0)
        font_size_unit_lab = wx.StaticText(self, -1, "pt")

        font_size_hbox = wx.BoxSizer(wx.HORIZONTAL)
        font_size_hbox.Add(self.font_size_box, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))
        font_size_hbox.Add(font_size_unit_lab, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        scroll_duration_lab = wx.StaticText(self, -1, "普通弹幕滚动时长")
        self.scroll_duration_box = wx.SpinCtrl(self, -1, min = 1, max = 15, initial = 0)
        scroll_duration_unit_lab = wx.StaticText(self, -1, "s")

        scroll_duration_hbox = wx.BoxSizer(wx.HORIZONTAL)
        scroll_duration_hbox.Add(self.scroll_duration_box, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))
        scroll_duration_hbox.Add(scroll_duration_unit_lab, 0, wx.ALL &  (~wx.TOP) & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        stay_duration_lab = wx.StaticText(self, -1, "顶部/底部弹幕停留时长")
        self.stay_duration_box = wx.SpinCtrl(self, -1, min = 1, max = 30, initial = 0)
        stay_duration_unit_lab = wx.StaticText(self, -1, "s")

        stay_duration_hbox = wx.BoxSizer(wx.HORIZONTAL)
        stay_duration_hbox.Add(self.stay_duration_box, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))
        stay_duration_hbox.Add(stay_duration_unit_lab, 0, wx.ALL &  (~wx.TOP) & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        rows_lab = wx.StaticText(self, -1, "弹幕显示行数")
        self.rows_box = wx.TextCtrl(self, -1, size = self.FromDIP((32, 24)), style = wx.TE_READONLY)
        rows_tooltip = ToolTip(self)
        rows_tooltip.set_tooltip("指定的垂直分辨率所能容纳的最大弹幕行数，与字体大小设置有关。\n\n计算方法：弹幕行数 = 垂直分辨率 / 字体大小，向下取整")
        height_lab = wx.StaticText(self, -1, "参考")
        self.height_choice = wx.Choice(self, -1, choices = list(resolution_map.keys()))
        self.height_choice.SetStringSelection("1080p")

        rows_hbox = wx.BoxSizer(wx.HORIZONTAL)
        rows_hbox.Add(self.rows_box, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))
        rows_hbox.Add(rows_tooltip, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        rows_hbox.Add(height_lab, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        rows_hbox.Add(self.height_choice, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))

        grid_box = wx.FlexGridSizer(3, 4, 0, 0)
        grid_box.Add(font_name_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        grid_box.Add(font_name_hbox, 0, wx.EXPAND)
        grid_box.Add(font_size_lab, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        grid_box.Add(font_size_hbox, 0, wx.EXPAND)
        grid_box.Add(scroll_duration_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
        grid_box.Add(scroll_duration_hbox, 0, wx.EXPAND)
        grid_box.Add(stay_duration_lab, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        grid_box.Add(stay_duration_hbox, 0, wx.EXPAND)
        grid_box.Add(rows_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
        grid_box.Add(rows_hbox, 0, wx.EXPAND)
        grid_box.AddSpacer(1)
        grid_box.AddSpacer(1)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(grid_box, 0, wx.EXPAND)

        self.SetSizer(vbox)

    def Bind_EVT(self):
        self.font_name_btn.Bind(wx.EVT_BUTTON, self.onChangeFontEVT)

        self.font_size_box.Bind(wx.EVT_SPINCTRL, self.onChangeFontSizeEVT)
        self.font_size_box.Bind(wx.EVT_TEXT, self.onChangeFontSizeEVT)

        self.height_choice.Bind(wx.EVT_CHOICE, self.onChangeHeightEVT)

    def init_data(self):
        danmaku = Config.Temp.ass_style.get("danmaku")

        font = self.GetFont()
        font.SetFaceName(danmaku.get("font_name"))

        self.set_font(font)
        self.font_size_box.SetValue(danmaku.get("font_size"))

        self.scroll_duration_box.SetValue(danmaku.get("scroll_duration"))
        self.stay_duration_box.SetValue(danmaku.get("stay_duration"))

        self.onChangeFontSizeEVT(0)
    
    def set_font(self, font: wx.Font):
        self.font_name_preview_lab.SetLabel(font.GetFaceName())
        self.font_name_preview_lab.SetFont(font)

        self.GetSizer().Layout()

    def onChangeFontEVT(self, event):
        dlg = wx.FontDialog(self)

        if dlg.ShowModal() == wx.ID_OK:
            font = dlg.GetFontData().GetChosenFont()

            self.set_font(font)

    def onChangeFontSizeEVT(self, event):
        rows = int(self.height / self.font_size_box.GetValue())

        self.rows_box.SetValue(str(rows))

    def onChangeHeightEVT(self, event):
        self.height = resolution_map.get(self.height_choice.GetStringSelection())

        self.onChangeFontSizeEVT(0)

    def get_option(self):
        return {
            "font_name": self.font_name_preview_lab.GetFont().GetFaceName(),
            "font_size": self.font_size_box.GetValue(),
            "scroll_duration": self.scroll_duration_box.GetValue(),
            "stay_duration": self.stay_duration_box.GetValue()
        }

class SubtitlePage(Panel):
    def __init__(self, parent):
        Panel.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

        self.init_data()

    def init_UI(self):
        font_name_lab = wx.StaticText(self, -1, "字体名称")
        self.font_name_preview_lab = wx.StaticText(self, -1, self.GetFont().GetFaceName())
        self.font_name_btn = wx.Button(self, -1, "更改", size = self.get_scaled_size((50, 24)))

        font_name_hbox = wx.BoxSizer(wx.HORIZONTAL)
        font_name_hbox.Add(self.font_name_preview_lab, 0, wx.ALL| wx.ALIGN_CENTER, self.FromDIP(6))
        font_name_hbox.Add(self.font_name_btn, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))

        font_size_lab = wx.StaticText(self, -1, "字体大小")
        self.font_size_box = wx.SpinCtrl(self, -1, min = 1, max = 100, initial = 0)
        font_size_unit_lab = wx.StaticText(self, -1, "pt")

        font_size_hbox = wx.BoxSizer(wx.HORIZONTAL)
        font_size_hbox.Add(self.font_size_box, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))
        font_size_hbox.Add(font_size_unit_lab, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        color_box = wx.StaticBox(self, -1, "颜色")
        
        self.primary_color_picker = ASSColorPicker(self, "主要颜色")
        self.border_color_picker = ASSColorPicker(self, "边框")
        self.shadow_color_picker = ASSColorPicker(self, "阴影")

        color_sbox = wx.StaticBoxSizer(color_box, wx.HORIZONTAL)
        color_sbox.Add(self.primary_color_picker, 0, wx.EXPAND)
        color_sbox.Add(self.border_color_picker, 0, wx.EXPAND)
        color_sbox.Add(self.shadow_color_picker, 0, wx.EXPAND)

        margin_box = wx.StaticBox(self, -1, "边距")

        self.left_margin_box = LabelSpinCtrl(self, "左边距", 10)
        self.right_margin_box = LabelSpinCtrl(self, "右边距", 10)
        self.vertical_margin_box = LabelSpinCtrl(self, "垂直边距", 10)

        margin_sbox = wx.StaticBoxSizer(margin_box, wx.HORIZONTAL)
        margin_sbox.Add(self.left_margin_box, 0, wx.ALL, self.FromDIP(6))
        margin_sbox.Add(self.right_margin_box, 0, wx.ALL, self.FromDIP(6))
        margin_sbox.Add(self.vertical_margin_box, 0, wx.ALL, self.FromDIP(6))

        self.align_radio_box = wx.RadioBox(self, -1, "对齐方式", choices = ["7", "8", "9", "4", "5", "6", "1", "2", "3"], majorDimension = 3)
        self.align_radio_box.SetToolTip("字幕在画面中位置的对齐方式，按照小键盘区布局")

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(margin_sbox, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))
        hbox.Add(self.align_radio_box, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))

        grid_box = wx.FlexGridSizer(1, 4, 0, 0)
        grid_box.Add(font_name_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        grid_box.Add(font_name_hbox, 0, wx.EXPAND)
        grid_box.Add(font_size_lab, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        grid_box.Add(font_size_hbox, 0, wx.EXPAND)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(grid_box, 0, wx.EXPAND)
        vbox.Add(color_sbox, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))
        vbox.Add(hbox, 0, wx.EXPAND)

        self.SetSizer(vbox)

    def Bind_EVT(self):
        self.font_name_btn.Bind(wx.EVT_BUTTON, self.onChangeFontEVT)

    def init_data(self):
        subtitle = Config.Temp.ass_style.get("subtitle")

        font = self.GetFont()
        font.SetFaceName(subtitle.get("font_name"))

        self.set_font(font)
        self.font_size_box.SetValue(subtitle.get("font_size"))

        self.align_radio_box.SetStringSelection(str(subtitle.get("alignment")))

        self.primary_color_picker.SetColour(subtitle.get("primary_color"))
        self.border_color_picker.SetColour(subtitle.get("border_color"))
        self.shadow_color_picker.SetColour(subtitle.get("shadow_color"))

    def set_font(self, font: wx.Font):
        self.font_name_preview_lab.SetLabel(font.GetFaceName())
        self.font_name_preview_lab.SetFont(font)

        self.GetSizer().Layout()

    def onChangeFontEVT(self, event):
        dlg = wx.FontDialog(self)

        if dlg.ShowModal() == wx.ID_OK:
            font = dlg.GetFontData().GetChosenFont()

            self.set_font(font)

    def get_option(self):
        def get_ass_style_color(window: wx.Window):
            color: wx.Colour = window.GetColour()
            return Color.convert_to_ass_style_color(color.GetAsString(wx.C2S_HTML_SYNTAX))

        return {
            "font_name": self.font_name_preview_lab.GetFont().GetFaceName(),
            "font_size": self.font_size_box.GetValue(),
            "alignment": int(self.align_radio_box.GetStringSelection()),
            "primary_color": get_ass_style_color(self.primary_color_picker),
            "border_color": get_ass_style_color(self.border_color_picker),
            "shadow_color": get_ass_style_color(self.shadow_color_picker)
        }

class CustomASSStyleDialog(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent, "自定义 ASS 样式")

        self.init_UI()

        self.Bind_EVT()

        self.CenterOnParent()

    def init_UI(self):
        type_lab = wx.StaticText(self, -1, "类型")
        self.type_choice = wx.Choice(self, -1, choices = ["弹幕", "字幕"])
        self.type_choice.SetSelection(0)

        type_hbox = wx.BoxSizer(wx.HORIZONTAL)
        type_hbox.Add(type_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        type_hbox.Add(self.type_choice, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))

        top_line = wx.StaticLine(self, -1)

        self.notebook = wx.Simplebook(self, -1)

        self.notebook.AddPage(DanmakuPage(self.notebook), "danmaku")
        self.notebook.AddPage(SubtitlePage(self.notebook), "subtitle")

        bottom_line = wx.StaticLine(self, -1)

        self.ok_btn = wx.Button(self, wx.ID_OK, "确定", size = self.get_scaled_size((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, "取消", size = self.get_scaled_size((80, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer(1)
        bottom_hbox.Add(self.ok_btn, 0, wx.ALL, self.FromDIP(6))
        bottom_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(type_hbox, 0, wx.EXPAND)
        vbox.Add(top_line, 0, wx.EXPAND)
        vbox.Add(self.notebook, 0, wx.EXPAND)
        vbox.Add(bottom_line, 0, wx.EXPAND)
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def Bind_EVT(self):
        self.type_choice.Bind(wx.EVT_CHOICE, self.onChangeTypeEVT)

        self.ok_btn.Bind(wx.EVT_BUTTON, self.onConfirmEVT)

    def onChangeTypeEVT(self, event):
        match self.type_choice.GetStringSelection():
            case "弹幕":
                self.notebook.ChangeSelection(0)
            
            case "字幕":
                self.notebook.ChangeSelection(1)

    def onConfirmEVT(self, event):
        for i in range(self.notebook.GetPageCount()):
            page = self.notebook.GetPageText(i)

            Config.Temp.ass_style[page] = self.notebook.GetPage(i).get_option()

        event.Skip()
