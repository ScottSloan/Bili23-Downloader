import wx
import gettext

from utils.common.style.icon_v4 import Icon, IconID
from utils.common.data.file_name import preview_data, field_data_folder
from gui.component.window.dialog import Dialog
from gui.component.button.bitmap_button import BitmapButton
from gui.component.misc.tooltip import ToolTip

_ = gettext.gettext

class EditFolderDialog(Dialog):
    def __init__(self, parent: wx.Window, data: dict):
        self.data = data
        self.type = data.get("type")

        Dialog.__init__(self, parent, _("编辑模板"))

        self.init_UI()

        self.init_data()

        self.CentreOnParent()

    def init_UI(self):
        template_lab = wx.StaticText(self, -1, _("文件夹名称模板"))
        template_tip = ToolTip(self)
        template_tip.set_tooltip(_("有关文件名模板的详细设置，请参考说明文档。"))
        self.help_btn = BitmapButton(self, bitmap = Icon.get_icon_bitmap(IconID.Help), tooltip = _("查看帮助"))

        top_hbox = wx.BoxSizer(wx.HORIZONTAL)
        top_hbox.Add(template_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        top_hbox.Add(template_tip, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        top_hbox.AddStretchSpacer()
        top_hbox.Add(self.help_btn, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))

        self.template_box = wx.TextCtrl(self, -1)

        template_hbox = wx.BoxSizer(wx.HORIZONTAL)
        template_hbox.Add(self.template_box, 1, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))

        preview_lab = wx.StaticText(self, -1, _("预览"))

        preview_hbox = wx.BoxSizer(wx.HORIZONTAL)
        preview_hbox.Add(preview_lab, 0, wx.ALL & (~wx.BOTTOM) | wx.ALIGN_CENTER, self.FromDIP(6))

        folder_name_lab = wx.StaticText(self, -1, _("文件夹名称："))
        self.folder_name_lab = wx.StaticText(self, -1, style = wx.ST_ELLIPSIZE_START)

        folder_name_hbox = wx.BoxSizer(wx.HORIZONTAL)
        folder_name_hbox.Add(folder_name_lab, 0, wx.ALL & (~wx.RIGHT) | wx.ALIGN_CENTER, self.FromDIP(6))
        folder_name_hbox.Add(self.folder_name_lab, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        preview_vbox = wx.BoxSizer(wx.VERTICAL)
        preview_vbox.Add(preview_hbox, 0, wx.EXPAND)
        preview_vbox.Add(folder_name_hbox, 0, wx.EXPAND)

        field_lab = wx.StaticText(self, -1, _("可用字段列表（双击列表项目可添加字段）"))
        field_tip = ToolTip(self)
        field_tip.set_tooltip(_("同一字段可重复添加多次，且可同时用于子目录和文件名部分。\n\n对于时间字段的格式设置，请参考说明文档。"))

        field_hbox = wx.BoxSizer(wx.HORIZONTAL)
        field_hbox.Add(field_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        field_hbox.Add(field_tip, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.field_list = wx.ListCtrl(self, -1, size = self.FromDIP((680, 200)), style = wx.LC_REPORT)

        field_vbox = wx.BoxSizer(wx.VERTICAL)
        field_vbox.Add(field_hbox, 0, wx.EXPAND)
        field_vbox.Add(self.field_list, 1, wx.ALL & (~wx.TOP) & (~wx.BOTTOM) | wx.EXPAND, self.FromDIP(6))

        self.ok_btn = wx.Button(self, wx.ID_OK, _("确定"), size = self.FromDIP((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, _("取消"), size = self.FromDIP((80, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(self.ok_btn, 0, wx.ALL, self.FromDIP(6))
        bottom_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(top_hbox, 0, wx.EXPAND)
        vbox.Add(template_hbox, 0, wx.EXPAND)
        vbox.Add(preview_vbox, 0, wx.EXPAND)
        vbox.Add(field_vbox, 0, wx.EXPAND)
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def init_data(self):
        self.init_list_column()
        self.init_list_data()

    def init_list_column(self):
        self.field_list.AppendColumn(_("字段名称"), width = self.FromDIP(210))
        self.field_list.AppendColumn(_("说明"), width = self.FromDIP(240))
        self.field_list.AppendColumn(_("示例"), width = -1)

    def init_list_data(self):
        for entry in field_data_folder.values():
            if self.type in entry.get("type"):
                self.field_list.Append([entry.get("name"), entry.get("description"), entry.get("example")])

        self.field_list.SetColumnWidth(2, width = -1)
