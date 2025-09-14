import wx

from utils.config import Config
from utils.common.style.icon_v4 import Icon, IconID
from utils.common.data.file_name import template_list

from gui.dialog.setting.file_name.edit_template import EditTemplateDialog

from gui.component.window.dialog import Dialog
from gui.component.button.bitmap_button import BitmapButton
from gui.component.misc.tooltip import ToolTip

class CustomFileNameDialog(Dialog):
    def __init__(self, parent: wx.Window):
        Dialog.__init__(self, parent, "自定义下载文件名")

        self.init_UI()

        self.Bind_EVT()

        self.init_data()

        self.CenterOnParent()

    def init_UI(self):
        template_lab = wx.StaticText(self, -1, "文件名模板（双击列表项目修改）")
        template_tip = ToolTip(self)
        template_tip.set_tooltip("建议详细阅读说明文档，再进行设置。\n\n对于收藏夹、个人空间和热榜，程序会自动识别其中的视频类型，按照相应的模板命名。")
        self.help_btn = BitmapButton(self, bitmap = Icon.get_icon_bitmap(IconID.Help), tooltip = "查看帮助")

        top_hbox = wx.BoxSizer(wx.HORIZONTAL)
        top_hbox.Add(template_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        top_hbox.Add(template_tip, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER)
        top_hbox.AddStretchSpacer()
        top_hbox.Add(self.help_btn, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))

        self.template_list = wx.ListCtrl(self, -1, size = self.FromDIP((550, 210)), style = wx.LC_REPORT)

        self.use_tmdb_chk = wx.CheckBox(self, -1, "下载剧集时，使用刮削软件规范命名模板")

        self.ok_btn = wx.Button(self, wx.ID_OK, "确定", size = self.FromDIP((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, "取消", size = self.FromDIP((80, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(self.ok_btn, 0, wx.ALL, self.FromDIP(6))
        bottom_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(top_hbox, 0, wx.EXPAND)
        vbox.Add(self.template_list, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))
        vbox.Add(self.use_tmdb_chk, 0, wx.ALL & (~wx.BOTTOM), self.FromDIP(6))
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def Bind_EVT(self):
        self.template_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.onEditTemplateEVT)

        self.help_btn.Bind(wx.EVT_BUTTON, self.onHelpEVT)

        self.use_tmdb_chk.Bind(wx.EVT_CHECKBOX, self.onUseTMDBCheckEVT)

    def init_data(self):
        self.item_data_dict = {}

        self.use_tmdb_chk.SetValue(Config.Temp.use_tmdb)

        self.update_template_list()
        self.init_list_column()
        self.init_list_data()

        self.onUseTMDBCheckEVT(0)

    def init_list_column(self):
        self.template_list.AppendColumn("序号", width = self.FromDIP(40))
        self.template_list.AppendColumn("类别", width = self.FromDIP(85))
        self.template_list.AppendColumn("子类别", width = self.FromDIP(120))
        self.template_list.AppendColumn("生效", width = self.FromDIP(40))
        self.template_list.AppendColumn("文件名模板", width = -1)

    def init_list_data(self):
        for index, entry in enumerate(template_list):
            type = entry.get("type")
            template = entry.get("template", "")
            category = entry.get("category", "")
            subcategory = entry.get("subcategory", "")

            self.template_list.Append([type, category, subcategory, "√", template])

            self.item_data_dict[type] = {
                "type": type,
                "template": template,
                "link": entry.get("link"),
                "link_label": entry.get("link_label")
            }

            self.template_list.SetItemData(index, type)

        self.template_list.SetColumnWidth(4, width = -1)

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

        dlg = EditTemplateDialog(self, item_data)

        if dlg.ShowModal() == wx.ID_OK:
            self.template_list.SetItem(item, 4, dlg.get_template())

        self.template_list.SetColumnWidth(4, width = -1)

    def onOKEVT(self):
        Config.Temp.file_name_template_list.clear()

        for item in range(self.template_list.GetItemCount()):
            Config.Temp.file_name_template_list.append({
                "template": self.template_list.GetItemText(item, 4),
                "type": self.template_list.GetItemData(item)
            })
            
        Config.Temp.use_tmdb = self.use_tmdb_chk.GetValue()

    def onHelpEVT(self, event: wx.CommandEvent):
        wx.LaunchDefaultBrowser("https://bili23.scott-sloan.cn/doc/use/advanced/custom_file_name.html")

    def onUseTMDBCheckEVT(self, event: wx.CommandEvent):
        # reset
        self.template_list.SetItem(4, 3, "")
        self.template_list.SetItem(5, 3, "")

        # set
        if self.use_tmdb_chk.GetValue():
            self.template_list.SetItem(5, 3, "√")
        else:
            self.template_list.SetItem(4, 3, "√")
