import wx

from utils.common.style.font import SysFont

from gui.component.panel.panel import Panel

class FontStaticBox(Panel):
    def __init__(self, parent):
        Panel.__init__(self, parent)

        self.init_UI()

    def init_UI(self):
        font_box = wx.StaticBox(self, -1, "字体")

        self.font_name_choice = wx.Choice(font_box, -1, choices = SysFont.sys_font_list)

        self.font_size_box = wx.SpinCtrl(font_box, -1, min = 1, max = 100, initial = 0)
        font_size_unit_lab = wx.StaticText(font_box, -1, "pt")

        font_hbox = wx.BoxSizer(wx.HORIZONTAL)
        font_hbox.Add(self.font_name_choice, 0, wx.ALL, self.FromDIP(6))
        font_hbox.Add(self.font_size_box, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))
        font_hbox.Add(font_size_unit_lab, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.bold_chk = wx.CheckBox(font_box, -1, "粗体")
        self.italic_chk = wx.CheckBox(font_box, -1, "斜体")
        self.underline_chk = wx.CheckBox(font_box, -1, "下划线")
        self.strikeout_chk = wx.CheckBox(font_box, -1, "删除线")

        shape_hbox = wx.BoxSizer(wx.HORIZONTAL)
        shape_hbox.Add(self.bold_chk, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        shape_hbox.Add(self.italic_chk, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        shape_hbox.Add(self.underline_chk, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        shape_hbox.Add(self.strikeout_chk, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))

        font_sbox = wx.StaticBoxSizer(font_box, wx.VERTICAL)
        font_sbox.Add(font_hbox, 0, wx.EXPAND)
        font_sbox.Add(shape_hbox, 0, wx.EXPAND)
        
        self.SetSizer(font_sbox)

    def init_data(self, data: dict):
        self.font_name_choice.SetStringSelection(data.get("font_name"))
        self.font_size_box.SetValue(data.get("font_size"))
        self.bold_chk.SetValue(data.get("bold"))
        self.italic_chk.SetValue(data.get("italic"))
        self.underline_chk.SetValue(data.get("underline"))
        self.strikeout_chk.SetValue(data.get("strikeout"))

    def get_option(self):
        return {
            "font_name": self.font_name_choice.GetStringSelection(),
            "font_size": self.font_size_box.GetValue(),
            "bold": int(self.bold_chk.GetValue()),
            "italic": int(self.italic_chk.GetValue()),
            "underline": int(self.underline_chk.GetValue()),
            "strikeout": int(self.strikeout_chk.GetValue())
        }