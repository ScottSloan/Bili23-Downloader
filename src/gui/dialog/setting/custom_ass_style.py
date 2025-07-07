import wx

from gui.component.text_ctrl.text_ctrl import TextCtrl

from gui.component.window.dialog import Dialog
from gui.component.panel.panel import Panel

from gui.component.text_ctrl.text_ctrl import TextCtrl

class PreviewPanel(Panel):
    def __init__(self, parent):
        Panel.__init__(self, parent)

        self.SetBackgroundColour("black")

        self.SetMinSize((320, 180))

        self.show_preview()

    def show_preview(self):
        print(self.GetSize())
    
class DanmakuPage(Panel):
    def __init__(self, parent):
        Panel.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

    def init_UI(self):
        font_name_lab = wx.StaticText(self, -1, "字体名称")
        self.font_name_preview_lab = wx.StaticText(self, -1, self.GetFont().GetFaceName())
        self.font_name_btn = wx.Button(self, -1, "更改", size = self.get_scaled_size((50, 24)))

        font_name_hbox = wx.BoxSizer(wx.HORIZONTAL)
        font_name_hbox.Add(self.font_name_preview_lab, 0, wx.ALL| wx.ALIGN_CENTER, self.FromDIP(6))
        font_name_hbox.Add(self.font_name_btn, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))

        font_size_lab = wx.StaticText(self, -1, "字体大小")
        self.font_size_box = wx.SpinCtrl(self, -1, min = 1, max = 100, initial = 48)
        font_size_unit_lab = wx.StaticText(self, -1, "像素")

        font_size_hbox = wx.BoxSizer(wx.HORIZONTAL)
        font_size_hbox.Add(self.font_size_box, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))
        font_size_hbox.Add(font_size_unit_lab, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        scroll_duration_lab = wx.StaticText(self, -1, "普通弹幕滚动时长")
        self.scroll_duration_choice = wx.SpinCtrl(self, -1, min = 1, max = 15, initial = 10)
        scroll_duration_unit_lab = wx.StaticText(self, -1, "s")

        scroll_duration_hbox = wx.BoxSizer(wx.HORIZONTAL)
        scroll_duration_hbox.Add(self.scroll_duration_choice, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))
        scroll_duration_hbox.Add(scroll_duration_unit_lab, 0, wx.ALL &  (~wx.TOP) & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        stay_duration_lab = wx.StaticText(self, -1, "顶部/底部弹幕停留时长")
        self.stay_duration_box = wx.SpinCtrl(self, -1, min = 1, max = 30, initial = 5)
        stay_duration_unit_lab = wx.StaticText(self, -1, "s")

        stay_duration_hbox = wx.BoxSizer(wx.HORIZONTAL)
        stay_duration_hbox.Add(self.stay_duration_box, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))
        stay_duration_hbox.Add(stay_duration_unit_lab, 0, wx.ALL &  (~wx.TOP) & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        grid_box = wx.FlexGridSizer(2, 4, 0, 0)
        grid_box.Add(font_name_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        grid_box.Add(font_name_hbox, 0, wx.EXPAND)
        grid_box.Add(font_size_lab, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        grid_box.Add(font_size_hbox, 0, wx.EXPAND)
        grid_box.Add(scroll_duration_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
        grid_box.Add(scroll_duration_hbox, 0, wx.EXPAND)
        grid_box.Add(stay_duration_lab, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        grid_box.Add(stay_duration_hbox, 0, wx.EXPAND)

        preview_lab = wx.StaticText(self, -1, "预览")

        preview_panel = PreviewPanel(self)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(grid_box, 0, wx.EXPAND)
        vbox.Add(preview_lab, 0, wx.ALL, self.FromDIP(6))
        vbox.Add(preview_panel, 1, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))

        self.SetSizer(vbox)

    def Bind_EVT(self):
        self.font_name_btn.Bind(wx.EVT_BUTTON, self.onChangeFont)

    def onChangeFont(self, event):
        dlg = wx.FontDialog(self)

        if dlg.ShowModal() == wx.ID_OK:
            font = dlg.GetFontData().GetChosenFont()

            self.font_name_preview_lab.SetLabel(font.GetFaceName())
            self.font_name_preview_lab.SetFont(font)

            self.GetSizer().Layout()
        
class SubtitlePage(Panel):
    def __init__(self, parent):
        Panel.__init__(self, parent)

        self.init_UI()

    def init_UI(self):
        video_resolution_lab = wx.StaticText(self, -1, "视频分辨率")
        self.video_width_box = TextCtrl(self, -1, size = self.get_scaled_size((60, 24)))
        video_resolution_x_lab = wx.StaticText(self, -1, "x")
        self.video_height_box = TextCtrl(self, -1, size = self.get_scaled_size((60, 24)))

        video_resolution_hbox = wx.BoxSizer(wx.HORIZONTAL)
        video_resolution_hbox.Add(video_resolution_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        video_resolution_hbox.Add(self.video_width_box, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))
        video_resolution_hbox.Add(video_resolution_x_lab, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        video_resolution_hbox.Add(self.video_height_box, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(video_resolution_hbox, 0, wx.EXPAND)

        self.SetSizer(vbox)

class CustomASSStyleDialog(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent, "自定义 ASS 样式")

        self.init_UI()

        self.Bind_EVT()

        self.CenterOnParent()

    def init_UI(self):
        type_lab = wx.StaticText(self, -1, "类型")
        self.type_choice = wx.Choice(self, -1)

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
        pass

    def set_option(self):
        pass