import wx
import wx.adv
import gettext

from utils.common.style.icon_v4 import Icon, IconID
from utils.common.data.file_name import preview_data, field_data_folder
from utils.common.regex import Regex
from utils.common.formatter.file_name_v2 import FileNameFormatter
from utils.common.enums import TemplateType

from gui.component.window.dialog import Dialog
from gui.component.button.bitmap_button import BitmapButton
from gui.component.misc.tooltip import ToolTip

_ = gettext.gettext

class TemplateValidator:
    def __init__(self, template: str, field_dict: dict, strict_naming: bool):
        self.template = template
        self.field_dict = field_dict
        self.strict_naming = strict_naming

    def validate(self):
        try:
            self.check()

            return {
                "result": True,
                "msg": "success",
                "folder_name": self.get_folder_name()
            }

        except Exception as e:
            import traceback
            print(traceback.format_exc())

            return {
                "result": False,
                "msg": self.get_err_msg(e),
                "folder_name": ""
            }

    def check(self):
        if not self.template:
            raise ValueError("empty")
        
        if self.check_sep():
            raise ValueError("sep")
        
        if self.check_sep_starts():
            raise ValueError("sep starts")
        
        if self.check_illegal_chars():
            raise ValueError("illegal")
        
    def check_sep(self):
        return "\\" in self.template
    
    def check_sep_starts(self):
        return self.template.startswith("/")

    def check_illegal_chars(self):        
        if Regex.find_illegal_chars_ex(self.template):
            return True

    def get_folder_name(self):
        return FileNameFormatter.format_file_name(self.template, field_dict = self.field_dict)
    
    def get_err_msg(self, e: Exception):
        match e:
            case ValueError():
                match str(e):
                    case "empty":
                        return _("模板名不能为空")
                    
                    case "sep":
                        return _("路径分隔符不正确，请使用正斜杠 /")
                    
                    case "sep starts":
                        return _("不能以 / 开头")

                    case "illegal":
                        return _("不能包含 <>:\"\\|?* 之中任何字符")

                    case msg if msg.startswith(("Single", "expected", "unexpected", "unmatched")):
                        return _("字段名必须以 {} 包裹")

                    case _:
                        return str(e)
                    
            case KeyError():
                return _("未知字段 %s" % str(e))
            
            case IndexError():
                return _("字段名不能为空")

            case _:
                return str(e)

class EditFolderDialog(Dialog):
    def __init__(self, parent: wx.Window, data: dict):
        self.data = data
        self.type = data.get("type")

        Dialog.__init__(self, parent, _("编辑模板"))

        self.init_UI()

        self.Bind_EVT()

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

    def Bind_EVT(self):
        self.template_box.Bind(wx.EVT_TEXT, self.onTextEVT)

        self.field_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.onAddFieldEVT)

        self.help_btn.Bind(wx.EVT_BUTTON, self.onHelpEVT)

    def init_data(self):
        self.init_list_column()
        self.init_list_data()

        self.field_dict = self.get_field_dict()

        self.init_template()

    def init_list_column(self):
        self.field_list.AppendColumn(_("字段名称"), width = self.FromDIP(210))
        self.field_list.AppendColumn(_("说明"), width = self.FromDIP(240))
        self.field_list.AppendColumn(_("示例"), width = -1)

    def init_list_data(self):
        for entry in field_data_folder.values():
            if self.type in entry.get("type"):
                self.field_list.Append([entry.get("name"), entry.get("description"), entry.get("example")])

        self.field_list.SetColumnWidth(2, width = -1)

    def init_template(self):
        self.template_box.SetValue(self.data["template"]["0"])

    def onTextEVT(self, event: wx.CommandEvent):
        template = self.template_box.GetValue()

        validator = TemplateValidator(template, self.field_dict, self.type == TemplateType.Bangumi_strict.value)

        result = validator.validate()
        flag = result.get("result")

        if flag:
            self.show_file_name(result.get("folder_name"))
            self.update_template()
        else:
            self.show_error_tip(result.get("msg"))
            self.show_file_name("")

        self.ok_btn.Enable(flag)

        self.folder_name_lab.Wrap(self.folder_name_lab.GetSize().width)
        self.Layout()

        event.Skip()

    def show_file_name(self, folder_name: str):
        self.folder_name_lab.SetLabel(folder_name)
        self.folder_name_lab.SetToolTip(folder_name)

    def show_error_tip(self, msg: str):
        tip = wx.adv.RichToolTip(_("模板格式错误"), msg)
        tip.SetIcon(wx.ICON_ERROR)

        tip.ShowFor(self.template_box)

        wx.Bell()

    def onAddFieldEVT(self, event: wx.ListEvent):
        field = self.field_list.GetItemText(self.field_list.GetFocusedItem(), 0)

        self.template_box.AppendText(field)

    def get_template(self):
        return self.data["template"]
    
    def update_template(self):
        self.data["template"]["0"] = self.template_box.GetValue()

    def get_field_dict(self):
        field_dict = preview_data.get(self.type)
        field_dict.update(preview_data.get(0))

        return field_dict
    
    def onHelpEVT(self, event: wx.CommandEvent):
        wx.LaunchDefaultBrowser("https://bili23.scott-sloan.cn/doc/use/advanced/custom_file_name.html")