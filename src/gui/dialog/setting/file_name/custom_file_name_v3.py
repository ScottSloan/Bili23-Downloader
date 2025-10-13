import wx
import gettext

from utils.config import Config
from utils.common.style.icon_v4 import Icon, IconID
from utils.common.data.file_name import template_list
from utils.common.enums import TemplateType

from gui.dialog.setting.file_name.edit_template import EditTemplateDialog
from gui.dialog.setting.file_name.edit_folder import EditFolderDialog

from gui.component.window.dialog import Dialog
from gui.component.button.bitmap_button import BitmapButton
from gui.component.misc.tooltip import ToolTip

_ = gettext.gettext

class CustomFileNameDialog(Dialog):
    def __init__(self, parent: wx.Window):
        Dialog.__init__(self, parent, _("自定义下载文件名"))

        self.init_UI()

        self.Bind_EVT()

        self.init_data()

        self.CenterOnParent()

    def init_UI(self):
        template_lab = wx.StaticText(self, -1, _("文件名模板（双击列表项目修改）"))
        template_tip = ToolTip(self)
        template_tip.set_tooltip(_("建议详细阅读说明文档，再进行设置"))
        self.help_btn = BitmapButton(self, bitmap = Icon.get_icon_bitmap(IconID.Help), tooltip = _("查看帮助"))

        top_hbox = wx.BoxSizer(wx.HORIZONTAL)
        top_hbox.Add(template_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        top_hbox.Add(template_tip, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        top_hbox.AddStretchSpacer()
        top_hbox.Add(self.help_btn, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))

        self.template_list = wx.ListCtrl(self, -1, size = self.FromDIP((550, 210)), style = wx.LC_REPORT)

        self.strict_naming_chk = wx.CheckBox(self, -1, _("下载剧集时，使用严格刮削命名模板"))
        strict_naming_tip = ToolTip(self)
        strict_naming_tip.set_tooltip(_("启用后，在下载剧集时，将会自动识别季数，并添加 SxxExx 标识。\n配合'下载视频元数据'选项，可同时刮削剧集信息，便于 Kodi、Plex 等媒体库软件的识别。"))

        strict_naming_hbox = wx.BoxSizer(wx.HORIZONTAL)
        strict_naming_hbox.Add(self.strict_naming_chk, 0, wx.ALL & (~wx.BOTTOM) | wx.ALIGN_CENTER, self.FromDIP(6))
        strict_naming_hbox.Add(strict_naming_tip, 0, wx.ALL & (~wx.LEFT) & (~wx.BOTTOM) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.ok_btn = wx.Button(self, wx.ID_OK, _("确定"), size = self.FromDIP((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, _("取消"), size = self.FromDIP((80, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(self.ok_btn, 0, wx.ALL, self.FromDIP(6))
        bottom_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(top_hbox, 0, wx.EXPAND)
        vbox.Add(self.template_list, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))
        vbox.Add(strict_naming_hbox, 0, wx.EXPAND)
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def Bind_EVT(self):
        self.template_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.onEditTemplateEVT)

        self.help_btn.Bind(wx.EVT_BUTTON, self.onHelpEVT)

    def init_data(self):
        self.item_data_dict = {}

        self.strict_naming_chk.SetValue(Config.Temp.strict_naming)

        self.update_template_list()

        self.init_list_column()
        self.init_list_data()

    def init_list_column(self):
        self.template_list.AppendColumn(_("序号"), width = self.FromDIP(40))
        self.template_list.AppendColumn(_("类别"), width = self.FromDIP(85))
        self.template_list.AppendColumn(_("子类别"), width = self.FromDIP(120))
        self.template_list.AppendColumn(_("文件名模板"), width = -1)

    def init_list_data(self):
        for index, entry in enumerate(template_list):
            type = entry.get("type")
            template = entry.get("template")
            category = entry.get("category")
            subcategory = entry.get("subcategory")

            self.template_list.Append([type, category, subcategory, template["0"]])

            self.item_data_dict[type] = {
                "type": type,
                "template": template,
                "link": entry.get("link"),
                "link_label": entry.get("link_label")
            }

            self.template_list.SetItemData(index, type)

        self.template_list.SetColumnWidth(3, width = -1)

    def update_template_list(self):
        for entry in Config.Temp.file_name_template_list:
            type = entry.get("type")
            template = entry.get("template")

            for list_entry in template_list:
                if list_entry.get("type") == type:
                    list_entry["template"] = template

    def onEditTemplateEVT(self, event: wx.ListEvent):
        item = self.template_list.GetFocusedItem()

        type = self.template_list.GetItemData(item)
        item_data = self.item_data_dict.get(type)

        if TemplateType(type) in [TemplateType.Favlist, TemplateType.Space]:
            dlg = EditFolderDialog(self, item_data)
        else:
            dlg = EditTemplateDialog(self, item_data)

        if dlg.ShowModal() == wx.ID_OK:
            template = dlg.get_template()

            self.template_list.SetItem(item, 3, template["0"])

            self.item_data_dict[type]["template"] = template

        self.template_list.SetColumnWidth(3, width = -1)

    def onOKEVT(self):
        Config.Temp.file_name_template_list.clear()

        for item in range(self.template_list.GetItemCount()):
            type = self.template_list.GetItemData(item)

            Config.Temp.file_name_template_list.append({
                "template": self.item_data_dict[type]["template"],
                "type": type
            })

        Config.Temp.strict_naming = self.strict_naming_chk.GetValue()

    def onHelpEVT(self, event: wx.CommandEvent):
        wx.LaunchDefaultBrowser("https://bili23.scott-sloan.cn/doc/use/advanced/custom_file_name.html")