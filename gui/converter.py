import wx

from gui.templates import Frame

from utils.tools import target_format_map, target_codec_map

class ConverterWindow(Frame):
    def __init__(self, parent):
        Frame.__init__(self, parent, "格式转换")

        self.SetSize(self.FromDIP((500, 230)))

        self.init_UI()

        self.CenterOnParent()

    def init_UI(self):
        input_lab = wx.StaticText(self.panel, -1, "输入")
        self.input_box = wx.TextCtrl(self.panel, -1, size = self.FromDIP((400, 24)))
        self.input_browse_btn = wx.Button(self.panel, -1, "浏览", size = self.FromDIP((60, 24)))

        input_hbox = wx.BoxSizer(wx.HORIZONTAL)
        input_hbox.Add(input_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        input_hbox.Add(self.input_box, 0, wx.ALL & (~wx.LEFT), 10)
        input_hbox.Add(self.input_browse_btn, 0, wx.ALL & (~wx.LEFT), 10)

        output_lab = wx.StaticText(self.panel, -1, "输出")
        self.output_box = wx.TextCtrl(self.panel, -1, size = self.FromDIP((400, 24)))
        self.output_browse_btn = wx.Button(self.panel, -1, "浏览", size = self.FromDIP((60, 24)))

        output_hbox = wx.BoxSizer(wx.HORIZONTAL)
        output_hbox.Add(output_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        output_hbox.Add(self.output_box, 0, wx.ALL & (~wx.LEFT), 10)
        output_hbox.Add(self.output_browse_btn, 0, wx.ALL & (~wx.LEFT), 10)

        target_format_lab = wx.StaticText(self.panel, -1, "目标格式")
        self.target_format_choice = wx.Choice(self.panel, -1, choices = list(target_format_map.keys()))

        target_codec_lab = wx.StaticText(self.panel, -1, "编码器")
        self.target_codec_choice = wx.Choice(self.panel, -1, choices = list(target_codec_map.keys()))

        target_bitrate_lab = wx.StaticText(self.panel, -1, "比特率")
        self.target_bitrate_box = wx.TextCtrl(self.panel, -1)
        target_bitrate_unit_lab = wx.StaticText(self.panel, -1, "kbit/s")

        target_params_hbox = wx.BoxSizer(wx.HORIZONTAL)
        target_params_hbox.Add(target_format_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        target_params_hbox.Add(self.target_format_choice, 0, wx.ALL & (~wx.LEFT), 10)
        target_params_hbox.Add(target_codec_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        target_params_hbox.Add(self.target_codec_choice, 0, wx.ALL & (~wx.LEFT), 10)
        target_params_hbox.Add(target_bitrate_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        target_params_hbox.Add(self.target_bitrate_box, 0, wx.ALL & (~wx.LEFT), 10)
        target_params_hbox.Add(target_bitrate_unit_lab, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, 10)

        self.progress_bar = wx.Gauge(self.panel, -1)

        self.start_btn = wx.Button(self.panel, -1, "开始转换", size = self.FromDIP((110, 30)))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(input_hbox, 0, wx.EXPAND)
        vbox.Add(output_hbox, 0, wx.EXPAND)
        vbox.Add(target_params_hbox, 0, wx.EXPAND)
        vbox.AddSpacer(self.FromDIP(10))
        vbox.Add(self.progress_bar, 0, wx.ALL | wx.EXPAND, 10)
        vbox.Add(self.start_btn, 0, wx.ALL | wx.ALIGN_RIGHT, 10)

        self.panel.SetSizerAndFit(vbox)
