import wx
import os
import re
import webbrowser

from utils.config import Config

from utils.common.map import scope_map, field_map, get_mapping_key_by_value
from utils.common.file_name_v2 import FileNameFormatter
from utils.common.data_type import DownloadTaskInfo
from utils.common.font import SysFont

from gui.component.dialog import Dialog
from gui.component.text_ctrl import TextCtrl
from gui.component.tooltip import ToolTip

class AddNewTemplateDialog(Dialog):
    def __init__(self, parent, scope_id: int, add_mode = True, template: str = ""):
        self.scope_id = scope_id
        self.add_mode = add_mode
        self.template = template

        Dialog.__init__(self, parent, f"{'添加' if add_mode else '修改'}文件名模板")

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

        self.CenterOnParent()

    def init_UI(self):
        template_lab = wx.StaticText(self, -1, "文件名模板（支持添加子目录）")
        template_tooltip = ToolTip(self)
        template_tooltip.set_tooltip('此处的文件名不包含后缀名，具体的后缀名程序将根据所下载的媒体类型自动添加\n\n在文件名前方添加路径分隔符（\\ 或 /），即可添加子目录，满足相应字段的视频将会被放置到同一个文件夹中，达到自动分类的效果。\n\n示例：\n\\{series_title}\\{number}_{title} （一级子目录）\n\\{up_name}\\{pubdatetime}\\{collection_title}\\{number}_{title} （多级子目录）')
        self.help_btn = wx.Button(self, -1, "帮助", size = self.get_scaled_size((60, 24)))

        template_hbox = wx.BoxSizer(wx.HORIZONTAL)
        template_hbox.Add(template_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        template_hbox.Add(template_tooltip, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        template_hbox.AddStretchSpacer()
        template_hbox.Add(self.help_btn, 0, wx.ALL, self.FromDIP(6))

        font = self.GetFont()
        font.SetFaceName(SysFont.get_monospaced_font())
        self.template_box = TextCtrl(self, -1, size = self.FromDIP((750 if self.scope_id in [0, 4] else 680, 24)))
        self.template_box.SetFont(font)

        self.error_msg_lab = wx.StaticText(self, -1, "")
        self.error_msg_lab.SetForegroundColour("red")

        preview_lab = wx.StaticText(self, -1, "预览")
        self.directory_lab = wx.StaticText(self, -1, "子目录：")
        self.file_name_lab = wx.StaticText(self, -1, "文件名：")

        field_lab = wx.StaticText(self, -1, "可用字段列表（双击列表项目可添加字段）")
        field_tooltip = ToolTip(self)
        field_tooltip.set_tooltip("字段名必须以 {} 包裹，可重复添加，但最终文件名部分长度不能超过 255\n\n时间字段中格式可自定义，具体用法请参考说明文档\n\n不同类型视频可用的字段有所不同，请留意")

        field_hbox = wx.BoxSizer(wx.HORIZONTAL)
        field_hbox.Add(field_lab, 0, wx.ALL & (~wx.BOTTOM) | wx.ALIGN_CENTER, self.FromDIP(6))
        field_hbox.Add(field_tooltip, 0, wx.ALL & (~wx.BOTTOM) & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.field_list = wx.ListCtrl(self, -1, size = self.FromDIP((750 if self.scope_id in [0, 4] else 680, 200)), style = wx.LC_REPORT)

        self.ok_btn = wx.Button(self, wx.ID_OK, "确定", size = self.FromDIP((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, "取消", size = self.FromDIP((80, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer(1)
        bottom_hbox.Add(self.ok_btn, 0, wx.ALL, self.FromDIP(6))
        bottom_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(template_hbox, 0, wx.EXPAND)
        vbox.Add(self.template_box, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM), self.FromDIP(6))
        vbox.Add(self.error_msg_lab, 0, wx.ALL, self.FromDIP(6))
        vbox.Add(preview_lab, 0, wx.ALL & (~wx.BOTTOM), self.FromDIP(6))
        vbox.Add(self.directory_lab, 0, wx.ALL & (~wx.BOTTOM), self.FromDIP(6))
        vbox.Add(self.file_name_lab, 0, wx.ALL, self.FromDIP(6))
        vbox.Add(field_hbox, 0, wx.EXPAND)
        vbox.Add(self.field_list, 1, wx.ALL & (~wx.BOTTOM) | wx.EXPAND, self.FromDIP(6))
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def Bind_EVT(self):
        self.field_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.onAddFieldEVT)

        self.template_box.Bind(wx.EVT_TEXT, self.onTextEVT)

        self.help_btn.Bind(wx.EVT_BUTTON, self.onHelpEVT)

    def init_utils(self):
        def init_list_column():
            self.field_list.AppendColumn("字段名称", width = self.FromDIP(170))
            self.field_list.AppendColumn("说明", width = self.FromDIP(200))
            self.field_list.AppendColumn("示例", width = self.FromDIP(200))
            self.field_list.AppendColumn("生效范围", width = self.FromDIP(160))

        def init_list_data():
            def get_scope():
                return "、".join([get_mapping_key_by_value(scope_map, i) for i in value["scope"] if i in [1, 2, 3]])
            
            for value in field_map.values():            
                if self.scope_id in value["scope"]:
                    self.field_list.Append([value["name"], value["description"], value["example"], get_scope()])

        init_list_column()

        init_list_data()

        self.template_box.SetValue(self.template)

        if self.scope_id in [1, 2, 3]:
            self.field_list.DeleteColumn(3)

    def onAddFieldEVT(self, event):
        field = self.field_list.GetItemText(self.field_list.GetFocusedItem(), 0)

        self.template_box.AppendText(field)

    def onTextEVT(self, event):
        def show_file_name():
            self.directory_lab.SetLabel(f"子目录：{os.path.dirname(file_name)}")
            self.file_name_lab.SetLabel(f"文件名：{os.path.basename(file_name)}")

        template = self.get_template()

        if not template or not os.path.basename(template):
            self.ok_btn.Enable(False)
            return

        try:
            file_name = self.check_template(template)

            show_file_name()

            self.error_msg_lab.SetLabel("")
            self.ok_btn.Enable(True)

        except Exception as e:
            self.show_error_msg(e)

        event.Skip()

    def onHelpEVT(self, event):
        webbrowser.open("https://bili23.scott-sloan.cn/doc/use/advanced/custom_file_name.html")

    def get_template(self):
        return self.template_box.GetValue()
    
    def check_template(self, template: str):
        def get_task_info():
            task_info = DownloadTaskInfo()
            task_info.number = 1
            task_info.zero_padding_number = "01"
            task_info.title = "第1话 孤独的转机"
            task_info.aid = 944573356
            task_info.bvid = "BV1yW4y1j7Ft"
            task_info.cid = 875212290
            task_info.ep_id = 693247
            task_info.season_id = 43164
            task_info.media_id = 28339735
            task_info.series_title = "孤独摇滚！"
            task_info.section_title = "正片"
            task_info.part_title = "分节"
            task_info.list_title = "合集"
            task_info.video_quality_id = 120
            task_info.audio_quality_id = 30251
            task_info.video_codec_id = 12
            task_info.duration = 256
            task_info.pubtime = 1667061000
            task_info.area = "中国大陆"
            task_info.zone_info = {
                "zone": "综合",
                "subzone": "动漫剪辑"
            }
            task_info.up_info = {
                "up_name": "哔哩哔哩番剧",
                "up_mid": 928123
            }

            return task_info
        
        if self.check_sep(template):
            raise ValueError("sep")
        
        file_name = FileNameFormatter.format_file_name(get_task_info(), template, basename = False)

        if re.search(r'[<>:"|?*\x00-\x1F]', file_name):
            raise ValueError("illegal")
        
        if len(os.path.basename(file_name)) > 255:
            raise ValueError("max length")

        return file_name
        
    def show_error_msg(self, e):
        match e:
            case ValueError():
                if str(e) == "sep":
                    msg = f"路径分隔符不正确，当前操作系统所使用的路径分割符为：{os.sep}"

                if str(e).startswith(("Single", "expected", "unexpected", "unmatched")):
                    msg = "字段名必须以 {} 包裹"

                if str(e).startswith("Invalid"):
                    msg = "时间格式无效"

                if str(e) == "illegal":
                    msg = '文件名和目录名不能包含 <>:"|?* 之中任何字符'

                if str(e) == "max length":
                    msg = "文件名长度超过 255"

            case IndexError() | KeyError():
                msg = "字段名无效"

            case _:
                msg = str(e)

        self.error_msg_lab.SetLabel(msg)
        self.directory_lab.SetLabel("子目录：")
        self.file_name_lab.SetLabel("文件名：")

        self.ok_btn.Enable(False)

    def check_sep(self, template: str):
        sep = "\\" if os.sep == "/" else "/"

        return sep in template

class CustomFileNameDialog(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent, "自定义下载文件名")

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

        self.CenterOnParent()

    def init_UI(self):
        template_lab = wx.StaticText(self, -1, "已添加的文件名模板")

        scope_lab = wx.StaticText(self, -1, "生效范围")
        self.scope_choice = wx.Choice(self, -1, choices = list(scope_map.keys()))
        self.scope_choice.SetSelection(0)
        scope_tooltip = ToolTip(self)
        scope_tooltip.set_tooltip("指定文件名模板的生效范围\n\n目前程序支持下载的视频分为三类：投稿视频、剧集（电影、番剧等）和课程\n\n所有类型：对三种类型的视频都生效\n投稿视频\\剧集\\课程：对相应类型的视频生效\n默认：未设置相应类型的文件名模板时所使用的默认值\n\n生效范围优先级：所有类型 > 投稿视频 = 剧集 = 课程 > 默认")
        self.add_btn = wx.Button(self, -1, "添加模板", size = self.get_scaled_size((80, 24)))

        top_hbox = wx.BoxSizer(wx.HORIZONTAL)
        top_hbox.Add(template_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        top_hbox.AddStretchSpacer()
        top_hbox.Add(scope_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        top_hbox.Add(self.scope_choice, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        top_hbox.Add(scope_tooltip, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        top_hbox.Add(self.add_btn, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.template_list = wx.ListCtrl(self, -1, size = self.FromDIP((650, 220)), style = wx.LC_REPORT)

        self.edit_btn = wx.Button(self, -1, "修改模板", size = self.get_scaled_size((80, 28)))
        self.delete_btn = wx.Button(self, -1, "删除模板", size = self.get_scaled_size((80, 28)))
        self.reset_btn = wx.Button(self, -1, "重置为默认值", size = self.get_scaled_size((100, 28)))

        action_hbox = wx.BoxSizer(wx.HORIZONTAL)
        action_hbox.Add(self.edit_btn, 0, wx.ALL & (~wx.BOTTOM), self.FromDIP(6))
        action_hbox.Add(self.delete_btn, 0, wx.ALL & (~wx.LEFT) & (~wx.BOTTOM), self.FromDIP(6))
        action_hbox.AddStretchSpacer()
        action_hbox.Add(self.reset_btn, 0, wx.ALL & (~wx.BOTTOM), self.FromDIP(6))

        bottom_line = wx.StaticLine(self, -1)

        self.ok_btn = wx.Button(self, wx.ID_OK, "确定", size = self.FromDIP((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, "取消", size = self.FromDIP((80, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer(1)
        bottom_hbox.Add(self.ok_btn, 0, wx.ALL, self.FromDIP(6))
        bottom_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(top_hbox, 0, wx.EXPAND)
        vbox.Add(self.template_list, 1, wx.ALL & (~wx.TOP) & (~wx.BOTTOM) | wx.EXPAND, self.FromDIP(6))
        vbox.Add(action_hbox, 0, wx.EXPAND)
        vbox.Add(bottom_line, 0, wx.ALL & (~wx.BOTTOM) | wx.EXPAND, self.FromDIP(6))
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def Bind_EVT(self):
        self.add_btn.Bind(wx.EVT_BUTTON, self.onAddEVT)
        self.edit_btn.Bind(wx.EVT_BUTTON, self.onEditEVT)
        self.delete_btn.Bind(wx.EVT_BUTTON, self.onDeleteEVT)
        self.reset_btn.Bind(wx.EVT_BUTTON, self.onResetEVT)

        self.ok_btn.Bind(wx.EVT_BUTTON, self.onConfirmEVT)

        self.template_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.onEditEVT)

    def init_utils(self):
        def init_list_column():
            self.template_list.AppendColumn("文件名模板", width = self.FromDIP(500))
            self.template_list.AppendColumn("生效范围", width = self.FromDIP(100))

        def init_list_data():
            for entry in Config.Temp.file_name_template_list:
                self.template_list.Append([entry["template"], get_mapping_key_by_value(scope_map, entry["scope"])])

        init_list_column()

        init_list_data()

    def onAddEVT(self, event):
        scope = self.scope_choice.GetStringSelection()
        scope_id = scope_map.get(scope)

        if self.check_existence(scope):
            wx.MessageDialog(self, "已有相同生效范围的字段\n\n列表中已有相同生效范围的字段，无法重复添加", "警告", wx.ICON_WARNING).ShowModal()
            return

        dlg = AddNewTemplateDialog(self, scope_id)

        if dlg.ShowModal() == wx.ID_OK:
            self.template_list.Append([dlg.get_template(), scope])

    def onEditEVT(self, event):
        item = self.template_list.GetFocusedItem()

        if item == -1:
            wx.MessageDialog(self, "修改文件名模板失败\n\n未选择要修改的文件名模板", "警告", wx.ICON_WARNING).ShowModal()
            return
        
        template = self.template_list.GetItemText(item, 0)
        scope_id = scope_map.get(self.template_list.GetItemText(item, 1))

        dlg = AddNewTemplateDialog(self, scope_id, add_mode = False, template = template)

        if dlg.ShowModal() == wx.ID_OK:
            new_template = dlg.get_template()

            self.template_list.SetItem(item, 0, new_template)

    def onDeleteEVT(self, event):
        item = self.template_list.GetFocusedItem()

        if item == -1:
            wx.MessageDialog(self, "删除文件名模板失败\n\n未选择要删除的文件名模板", "警告", wx.ICON_WARNING).ShowModal()
            return
        
        scope_id = scope_map.get(self.template_list.GetItemText(item, 1))

        if scope_id == 4:
            wx.MessageDialog(self, "删除文件名模板失败\n\n不能删除默认的文件名模板", "警告", wx.ICON_WARNING).ShowModal()
            return

        dlg = wx.MessageDialog(self, "删除文件名模板\n\n是否要删除该模板？", "提示", wx.ICON_WARNING | wx.YES_NO)

        if dlg.ShowModal() == wx.ID_YES:
            self.template_list.DeleteItem(item)

    def onResetEVT(self, event):
        dlg = wx.MessageDialog(self, "重置为默认值\n\n是否要重置为默认值？当前添加的文件名模板将会丢失", "警告", wx.ICON_WARNING | wx.YES_NO)

        if dlg.ShowModal() == wx.ID_YES:
            self.template_list.DeleteAllItems()

            self.template_list.Append(["{zero_padding_number} - {title}", "默认"])

    def onConfirmEVT(self, event):
        Config.Temp.file_name_template_list.clear()

        for i in range(self.template_list.GetItemCount()):
            Config.Temp.file_name_template_list.append({
                "template": self.template_list.GetItemText(i, 0),
                "scope": scope_map.get(self.template_list.GetItemText(i, 1))
            })

        event.Skip()

    def check_existence(self, scope: str):
        for i in range(self.template_list.GetItemCount()):
            if self.template_list.GetItemText(i, 1) == scope:
                return True
            