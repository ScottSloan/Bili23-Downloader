import wx
import wx.adv

from utils.common.style.icon_v4 import Icon, IconID
from utils.common.data.file_name import preview_data, field_data

from gui.component.window.dialog import Dialog
from gui.component.button.bitmap_button import BitmapButton

class EditTemplateDialog(Dialog):
    def __init__(self, parent: wx.Window, data: dict):
        self.type = data.get("type")

        Dialog.__init__(self, parent, "编辑模板")

        self.init_UI()

        self.Bind_EVT()

        self.init_data()

        self.CenterOnParent()

    def init_UI(self):
        template_lab = wx.StaticText(self, -1, "文件名模板")
        self.help_btn = BitmapButton(self, bitmap = Icon.get_icon_bitmap(IconID.Help), tooltip = "查看帮助")

        top_hbox = wx.BoxSizer(wx.HORIZONTAL)
        top_hbox.Add(template_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        top_hbox.AddStretchSpacer()
        top_hbox.Add(self.help_btn, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))

        self.template_box = wx.TextCtrl(self, -1)

        preview_lab = wx.StaticText(self, -1, "预览")
        self.preview_video_link = wx.adv.HyperlinkCtrl(self, -1, "BV12345")

        preview_hbox = wx.BoxSizer(wx.HORIZONTAL)
        preview_hbox.Add(preview_lab, 0, wx.ALL, self.FromDIP(6))
        preview_hbox.Add(self.preview_video_link, 0, wx.ALL, self.FromDIP(6))

        field_lab = wx.StaticText(self, -1, "可用字段列表（双击列表项目可添加字段）")
        self.field_list = wx.ListCtrl(self, -1, size = self.FromDIP((680, 200)), style = wx.LC_REPORT)

        field_hbox = wx.BoxSizer(wx.HORIZONTAL)
        field_hbox.Add(field_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))

        field_vbox = wx.BoxSizer(wx.VERTICAL)
        field_vbox.Add(field_hbox, 0, wx.EXPAND)
        field_vbox.Add(self.field_list, 1, wx.ALL & (~wx.TOP) & (~wx.BOTTOM) | wx.EXPAND, self.FromDIP(6))

        self.ok_btn = wx.Button(self, wx.ID_OK, "确定", size = self.FromDIP((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, "取消", size = self.FromDIP((80, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(self.ok_btn, 0, wx.ALL, self.FromDIP(6))
        bottom_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(top_hbox, 0, wx.EXPAND)
        vbox.Add(self.template_box, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))
        vbox.Add(preview_hbox, 0, wx.EXPAND)
        vbox.Add(field_vbox, 0, wx.EXPAND)
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def Bind_EVT(self):
        pass

    def init_data(self):
        self.init_list_column()
        self.init_list_data()

    def init_list_column(self):
        self.field_list.AppendColumn("字段名称", width = self.FromDIP(210))
        self.field_list.AppendColumn("说明", width = self.FromDIP(240))
        self.field_list.AppendColumn("示例", width = self.FromDIP(200))

    def init_list_data(self):
        for type in [0, self.type]:
            for key, value in preview_data.get(type).items():
                field_data[key]["example"] = str(value)

        for entry in field_data.values():
            if (example := entry.get("example")):
                self.field_list.Append([entry.get("name"), entry.get("description"), example])