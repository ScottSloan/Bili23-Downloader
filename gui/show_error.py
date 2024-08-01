import wx
import wx.adv

from gui.templates import ScrolledPanel

class ShowErrorDialog(wx.Dialog):
    def __init__(self, parent, log):
        self.log = log

        wx.Dialog.__init__(self, parent, -1, "错误信息")

        self.init_UI()

        self.init_error_log()

        self.CenterOnParent()

    def init_UI(self):
        self.detail_lab = wx.StaticText(self, -1, f"时间：{self.log['time']}   返回值：{self.log['return_code']}")

        top_border = wx.StaticLine(self, -1, style = wx.HORIZONTAL)

        self.log_panel = ScrolledPanel(self, size = self.FromDIP((450, 230)))
        self.log_panel.SetBackgroundColour("white")

        self.copy_btn = wx.Button(self, -1, "复制", size = self.FromDIP((80, 25)))
        self.close_btn = wx.Button(self, wx.ID_CANCEL, "关闭", size = self.FromDIP((80, 25)))

        bottom_border = wx.StaticLine(self, -1, style = wx.HORIZONTAL)

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(self.copy_btn, 0, wx.ALL, 10)
        bottom_hbox.Add(self.close_btn, 0, wx.ALL & (~wx.LEFT), 10)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.detail_lab, 0, wx.ALL, 10)
        vbox.Add(top_border, 0, wx.EXPAND)
        vbox.Add(self.log_panel, 0, wx.EXPAND)
        vbox.Add(bottom_border, 0, wx.EXPAND)
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

        self.SetBackgroundColour("white")

    def init_error_log(self):
        error_log_panel = ErrorLogPanel(self.log_panel, self.log)

        self.log_panel.sizer.Add(error_log_panel, 0, wx.EXPAND)

        self.log_panel.SetupScrolling(scroll_x = False)

        self.log_panel.Layout()
        self.log_panel.SetupScrolling(scroll_x = False)

class ErrorLogPanel(wx.Panel):
    def __init__(self, parent, log):
        self.log = log

        wx.Panel.__init__(self, parent, -1)

        self.init_UI()

    def init_UI(self):
        log_font: wx.Font = self.GetFont()
        log_font.SetPointSize(10)

        self.log_lab = wx.StaticText(self, -1, self.log["log"], size = self.FromDIP((430, 500)))
        self.log_lab.SetFont(log_font)

        self.log_lab.SetLabel()

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.log_lab, 0, wx.ALL | wx.EXPAND, 10)
        
        self.SetSizerAndFit(vbox)