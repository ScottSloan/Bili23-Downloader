import wx
import os
import wx.adv

from utils.common.style.icon_v4 import Icon, IconID
from utils.common.data.file_name import preview_data, field_data, preview_data_ex
from utils.common.regex import Regex
from utils.common.formatter.file_name_v2 import FileNameFormatter
from utils.common.datetime_util import DateTime
from utils.common.enums import TemplateType

from gui.component.window.dialog import Dialog
from gui.component.button.bitmap_button import BitmapButton
from gui.component.misc.tooltip import ToolTip

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
                "file_name": self.get_file_name()
            }

        except Exception as e:
            import traceback
            print(traceback.format_exc())

            return {
                "result": False,
                "msg": self.get_err_msg(e),
                "file_name": ""
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
        
        if self.check_strict_naming():
            raise ValueError("strict naming")
        
    def check_sep(self):
        return "\\" in self.template
    
    def check_sep_starts(self):
        return self.template.startswith("/")

    def check_illegal_chars(self):
        pattern = r"{time:|{pubtime:|{season_num:|{episode_num:"

        if Regex.search(pattern, self.template):
            temp = Regex.sub(pattern, "", self.template)
        else:
            temp = self.template
        
        if Regex.find_illegal_chars(temp):
            return True

    def check_strict_naming(self):
        if self.strict_naming:
            return not Regex.search(r"^{series_title_original}/{section_title_ex}", self.template)

    def get_file_name(self):
        self.field_dict["time"] = DateTime.now()
        self.field_dict["pubtime"] = DateTime.from_timestamp(1755633699)

        return FileNameFormatter.format_file_name(self.template, field_dict = self.field_dict)
    
    def get_err_msg(self, e: Exception):
        match e:
            case ValueError():
                match str(e):
                    case "empty":
                        return "模板名不能为空"
                    
                    case "sep":
                        return "路径分隔符不正确，请使用正斜杠 /"
                    
                    case "sep starts":
                        return "不能以 / 开头"
                    
                    case "illegal":
                        return """不能包含 <>:"|?* 之中任何字符"""
                    
                    case msg if msg.startswith(("Single", "expected", "unexpected", "unmatched")):
                        return "字段名必须以 {} 包裹"
                    
                    case "Invalid format string":
                        return "时间格式无效"
                    
                    case "strict naming":
                        return "编辑严格规范命名模板时，必须以 {series_title_original} 开头"
                    
                    case _:
                        return str(e)
                    
            case KeyError():
                return f"未知字段 {str(e)}"
            
            case IndexError():
                return "字段名不能为空"
                    
            case _:
                return str(e)

class EditTemplateDialog(Dialog):
    def __init__(self, parent: wx.Window, data: dict):
        self.data = data
        self.type = data.get("type")

        Dialog.__init__(self, parent, "编辑模板")

        self.init_UI()

        self.Bind_EVT()

        self.init_data()

        self.CenterOnParent()

    def init_UI(self):
        template_lab = wx.StaticText(self, -1, "文件名模板")
        template_tip = ToolTip(self)
        template_tip.set_tooltip("有关文件名模板的详细设置，请参考说明文档。")
        self.help_btn = BitmapButton(self, bitmap = Icon.get_icon_bitmap(IconID.Help), tooltip = "查看帮助")

        top_hbox = wx.BoxSizer(wx.HORIZONTAL)
        top_hbox.Add(template_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        top_hbox.Add(template_tip, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        top_hbox.AddStretchSpacer()
        top_hbox.Add(self.help_btn, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))

        self.template_box = wx.TextCtrl(self, -1)

        preview_lab = wx.StaticText(self, -1, "预览")

        preview_hbox = wx.BoxSizer(wx.HORIZONTAL)
        preview_hbox.Add(preview_lab, 0, wx.ALL & (~wx.BOTTOM) | wx.ALIGN_CENTER, self.FromDIP(6))

        directory_lab = wx.StaticText(self, -1, "子目录：")
        self.directory_lab = wx.StaticText(self, -1, style = wx.ST_ELLIPSIZE_START)

        file_name_lab = wx.StaticText(self, -1, "文件名：")
        self.file_name_lab = wx.StaticText(self, -1, style = wx.ST_ELLIPSIZE_START)

        directory_hbox = wx.BoxSizer(wx.HORIZONTAL)
        directory_hbox.Add(directory_lab, 0, wx.ALL & (~wx.RIGHT) & (~wx.BOTTOM) | wx.ALIGN_CENTER, self.FromDIP(6))
        directory_hbox.Add(self.directory_lab, 0, wx.ALL & (~wx.LEFT) & (~wx.BOTTOM) | wx.ALIGN_CENTER, self.FromDIP(6))

        file_name_hbox = wx.BoxSizer(wx.HORIZONTAL)
        file_name_hbox.Add(file_name_lab, 0, wx.ALL & (~wx.RIGHT) | wx.ALIGN_CENTER, self.FromDIP(6))
        file_name_hbox.Add(self.file_name_lab, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        preview_vbox = wx.BoxSizer(wx.VERTICAL)
        preview_vbox.Add(preview_hbox, 0, wx.EXPAND)
        preview_vbox.Add(directory_hbox, 0, wx.EXPAND)
        preview_vbox.Add(file_name_hbox, 0, wx.EXPAND)

        field_lab = wx.StaticText(self, -1, "可用字段列表（双击列表项目可添加字段）")
        field_tip = ToolTip(self)
        field_tip.set_tooltip("同一字段可重复添加多次，且可同时用于子目录和文件名部分。\n\n对于时间字段的格式设置，请参考说明文档。")
        link_lab = wx.StaticText(self, -1, "示例视频：")
        self.video_link = wx.adv.HyperlinkCtrl(self, -1, label = self.data.get("link_label"), url = self.data.get("link"))

        field_hbox = wx.BoxSizer(wx.HORIZONTAL)
        field_hbox.Add(field_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        field_hbox.Add(field_tip, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        field_hbox.AddStretchSpacer()
        field_hbox.Add(link_lab, 0, wx.ALL & (~wx.RIGHT) | wx.ALIGN_CENTER, self.FromDIP(6))
        field_hbox.Add(self.video_link, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.field_list = wx.ListCtrl(self, -1, size = self.FromDIP((680, 200)), style = wx.LC_REPORT)

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

        self.template_box.SetValue(self.data.get("template"))

    def init_list_column(self):
        self.field_list.AppendColumn("字段名称", width = self.FromDIP(210))
        self.field_list.AppendColumn("说明", width = self.FromDIP(240))
        self.field_list.AppendColumn("示例", width = -1)

    def init_list_data(self):
        for type in [0, self.type]:
            for key, value in preview_data.get(type).items():
                field_data[key]["example"] = str(value)

        for entry in field_data.values():
            if self.type in entry.get("type"):
                self.field_list.Append([entry.get("name"), entry.get("description"), entry.get("example")])

        self.field_list.SetColumnWidth(2, width = -1)

    def onTextEVT(self, event: wx.CommandEvent):
        validator = TemplateValidator(self.get_template(), self.field_dict, self.type == TemplateType.Bangumi_strict.value)

        result = validator.validate()
        flag = result.get("result")

        if flag:
            self.show_file_name(result.get("file_name"))

        else:
            self.show_error_tip(result.get("msg"))
            self.show_file_name("")

        self.ok_btn.Enable(flag)

        self.file_name_lab.Wrap(self.file_name_lab.GetSize().width)
        self.Layout()

        event.Skip()

    def onAddFieldEVT(self, event: wx.ListEvent):
        field = self.field_list.GetItemText(self.field_list.GetFocusedItem(), 0)

        self.template_box.AppendText(field)

    def show_file_name(self, file_name: str):
        dirname = os.path.dirname(file_name)
        basename = os.path.basename(file_name)

        self.directory_lab.SetLabel(dirname)
        self.directory_lab.SetToolTip(dirname)
        self.file_name_lab.SetLabel(basename)
        self.file_name_lab.SetToolTip(basename)

    def show_error_tip(self, msg: str):
        tip = wx.adv.RichToolTip("模板格式错误", msg)
        tip.SetIcon(wx.ICON_ERROR)

        tip.ShowFor(self.template_box)

        wx.Bell()

    def get_template(self):
        return self.template_box.GetValue()
    
    def get_field_dict(self):
        field_dict = preview_data.get(self.type)
        field_dict.update(preview_data.get(0))
        field_dict.update(preview_data_ex.get(self.type))

        return field_dict
    
    def onHelpEVT(self, event: wx.CommandEvent):
        wx.LaunchDefaultBrowser("https://bili23.scott-sloan.cn/doc/use/advanced/custom_file_name.html")