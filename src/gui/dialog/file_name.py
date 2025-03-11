import wx
from datetime import datetime

from utils.common.map import file_name_fields_map, get_mapping_key_by_value

from gui.templates import TextCtrl

class CustomFileNameDialog(wx.Dialog):
    def __init__(self, parent, template: str):
        self.template = template

        wx.Dialog.__init__(self, parent, -1, "自定义下载文件名")

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

        self.CenterOnParent()

    def init_UI(self):
        available_lab = wx.StaticText(self, -1, "可用字段")
        self.available_choice = wx.Choice(self, -1, choices = list(file_name_fields_map.values()))
        self.add_btn = wx.Button(self, -1, "添加字段", size = self.FromDIP((80, 28)))

        available_hbox = wx.BoxSizer(wx.HORIZONTAL)
        available_hbox.Add(available_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        available_hbox.Add(self.available_choice, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, 10)
        available_hbox.Add(self.add_btn, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, 10)

        template_lab = wx.StaticText(self, -1, "文件名模板")
        self.template_box = TextCtrl(self, -1, size = self.FromDIP((350, 24)))

        template_hbox = wx.BoxSizer(wx.HORIZONTAL)
        template_hbox.Add(template_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, 10)
        template_hbox.Add(self.template_box, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.ALIGN_CENTER, 10)

        self.error_icon = wx.StaticBitmap(self, -1, wx.ArtProvider().GetBitmap(wx.ART_ERROR, size = self.FromDIP((16, 16))), size = self.FromDIP((16, 16)))
        self.error_lab = wx.StaticText(self, -1)
        self.error_lab.SetForegroundColour(wx.Colour(250, 42, 45))

        error_hbox = wx.BoxSizer(wx.HORIZONTAL)
        error_hbox.AddSpacer(template_lab.GetSize()[0])
        error_hbox.Add(self.error_icon, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM), 10)
        error_hbox.Add(self.error_lab, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM) & (~wx.LEFT), 10)

        self.preview_lab = wx.StaticText(self, -1, "预览：")

        self.ok_btn = wx.Button(self, wx.ID_OK, "确定", size = self.FromDIP((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, "取消", size = self.FromDIP((80, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer(1)
        bottom_hbox.Add(self.ok_btn, 0, wx.ALL & (~wx.TOP), 10)
        bottom_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), 10)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(available_hbox, 0, wx.EXPAND)
        vbox.Add(template_hbox, 0, wx.EXPAND)
        vbox.Add(error_hbox, 0, wx.EXPAND)
        vbox.Add(self.preview_lab, 0, wx.ALL, 10)
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def Bind_EVT(self):
        self.add_btn.Bind(wx.EVT_BUTTON, self.onAddFieldEVT)
        self.template_box.Bind(wx.EVT_TEXT, self.onTextEVT)

    def init_utils(self):
        self.template_box.SetValue(self.template)

        self.error_icon.Show(False)
        self.Layout()

    def show_preview_file_name(self):
        date_field = datetime.now().strftime("%Y-%m-%d")
        time_field = datetime.now().strftime("%H:%M:%S")
        datetime_field = f"{date_field} {time_field}"
        timestamp_field = str(int(datetime.now().timestamp()))
        index_field = "1"
        index_with_zero_field = "01"
        title_field = "《孤独摇滚》第1话 孤独的转机"
        bvid_field = "BV1yW4y1j7Ft"
        cid_field = "875212290"

        template = str(self.template_box.GetValue())
        preview = template.format(date = date_field, time = time_field, datetime = datetime_field, timestamp = timestamp_field, index = index_field, index_with_zero = index_with_zero_field, title = title_field, bvid = bvid_field, cid = cid_field)

        self.preview_lab.SetLabel(f"预览：{preview}")

    def onTextEVT(self, event):
        try:
            self.show_preview_file_name()

            self.check_pass()

        except Exception as e:
            self.syntax_error(str(e))

        event.Skip()

    def onAddFieldEVT(self, event):
        field_name = get_mapping_key_by_value(file_name_fields_map, self.available_choice.GetStringSelection())

        self.template_box.AppendText("{" + field_name + "}")

    def check_pass(self):
        self.error_icon.Show(False)
        self.error_lab.SetLabel("")

        self.ok_btn.Enable(True)

    def syntax_error(self, e: str):
        self.error_icon.Show(True)

        if e.startswith("Single") or e.startswith("expected"):
            self.error_lab.SetLabel("字段名必须以 {} 包裹")
        else:
            self.error_lab.SetLabel("字段名错误")

        self.preview_lab.SetLabel("预览：-")

        self.ok_btn.Enable(False)

        self.Layout()

    def get_template(self):
        return self.template_box.GetValue()