import wx
import os
import webbrowser

from utils.config import Config

from utils.common.map import scope_map, field_map, get_mapping_key_by_value
from utils.common.file_name_v2 import FileNameFormatter
from utils.common.data_type import DownloadTaskInfo

from gui.component.dialog import Dialog
from gui.component.text_ctrl import TextCtrl
from gui.component.tooltip import ToolTip

class AddNewTemplateDialog(Dialog):
    def __init__(self, parent, scope_id: int):
        self.scope_id = scope_id

        Dialog.__init__(self, parent, "添加文件名模板")

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

        self.CenterOnParent()

    def init_UI(self):
        template_lab = wx.StaticText(self, -1, "文件名模板（支持添加子目录）")
        template_tooltip = ToolTip(self)
        template_tooltip.set_tooltip('此处的文件名不包含后缀名，具体的后缀名程序将根据所下载的媒体类型自动添加\n\n在文件名前方加入路径分隔符（\\ 或 /），即可添加子目录，满足相应字段的视频将会放在同一个文件夹中\n\n示例：\n\\{series_title}\\{number}_{title} （一级子目录）\n\\{up_name}\\{pubdatetime}\\{collection_title}\\{number}_{title} （多级子目录）\n\n空字段值将默认使用 null 替代')
        self.help_btn = wx.Button(self, -1, "帮助", size = self.get_scaled_size((60, 24)))

        template_hbox = wx.BoxSizer(wx.HORIZONTAL)
        template_hbox.Add(template_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        template_hbox.Add(template_tooltip, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        template_hbox.AddStretchSpacer()
        template_hbox.Add(self.help_btn, 0, wx.ALL, self.FromDIP(6))

        self.template_box = TextCtrl(self, -1, size = self.FromDIP((610, 24)))

        self.error_msg_lab = wx.StaticText(self, -1, "")
        self.error_msg_lab.SetForegroundColour("red")

        preview_lab = wx.StaticText(self, -1, "预览")
        self.subdirectory_lab = wx.StaticText(self, -1, "子目录：")
        self.file_name_lab = wx.StaticText(self, -1, "文件名：")

        field_lab = wx.StaticText(self, -1, "可用字段列表（双击添加字段）")
        self.field_list = wx.ListCtrl(self, -1, style = wx.LC_REPORT)

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
        vbox.Add(self.subdirectory_lab, 0, wx.ALL & (~wx.BOTTOM), self.FromDIP(6))
        vbox.Add(self.file_name_lab, 0, wx.ALL, self.FromDIP(6))
        vbox.Add(field_lab, 0, wx.ALL & (~wx.BOTTOM), self.FromDIP(6))
        vbox.Add(self.field_list, 1, wx.ALL & (~wx.BOTTOM) | wx.EXPAND, self.FromDIP(6))
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def Bind_EVT(self):
        self.field_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.onAddFieldEVT)

        self.template_box.Bind(wx.EVT_TEXT, self.onTextEVT)

        self.help_btn.Bind(wx.EVT_BUTTON, self.onHelpEVT)

    def init_utils(self):
        def init_list_column():
            self.field_list.AppendColumn("字段名称", width = self.FromDIP(180))
            self.field_list.AppendColumn("说明", width = self.FromDIP(220))
            self.field_list.AppendColumn("示例", width = self.FromDIP(200))

        def init_list_data():
            for value in field_map.values():            
                if self.scope_id in value["scope"]:
                    self.field_list.Append([value["name"], value["description"], value["example"]])

        init_list_column()

        init_list_data()

    def onAddFieldEVT(self, event):
        field = self.field_list.GetItemText(self.field_list.GetFocusedItem(), 0)

        self.template_box.AppendText(field)

    def onTextEVT(self, event):
        def show_file_name():
            self.subdirectory_lab.SetLabel(f"子目录：{os.path.dirname(file_name)}")
            self.file_name_lab.SetLabel(f"文件名：{os.path.basename(file_name)}")

        template = self.get_template()

        try:
            file_name = self.check_template(template)

            show_file_name()

            self.error_msg_lab.SetLabel("")

        except Exception as e:
            self.show_error_msg(e)

        event.Skip()

    def onHelpEVT(self, event):
        webbrowser.open("")

    def get_template(self):
        return self.template_box.GetValue()
    
    def check_template(self, template: str):
        def get_task_info():
            task_info = DownloadTaskInfo()
            task_info.number = 1
            task_info.zero_padding_number = "01"
            task_info.title = "《孤独摇滚》第1话 孤独的转机"
            task_info.aid = 944573356
            task_info.bvid = "BV1yW4y1j7Ft"
            task_info.cid = 875212290
            task_info.ep_id = 693247
            task_info.season_id = 43164
            task_info.media_id = 28339735
            task_info.series_title = "《孤独摇滚》"
            task_info.video_quality_id = 120
            task_info.audio_quality_id = 30251
            task_info.video_codec_id = 12
            task_info.duration = 256
            task_info.pubtime = 1667061000
            task_info.area = "中国大陆"
            task_info.tname_info = {
                "tname": "综合",
                "subtname": "动漫剪辑"
            }
            task_info.up_info = {
                "up_name": "哔哩哔哩番剧",
                "up_mid": 928123
            }

            return task_info
        
        if self.check_sep(template):
            raise ValueError("sep")
        
        return FileNameFormatter.format_file_name(get_task_info(), template)
        
    def show_error_msg(self, e):
        match str(e):
            case "sep":
                msg = f"路径分隔符不正确，当前操作系统所使用的路径分割符为：{os.sep}"

            case _:
                msg = str(e)

        self.error_msg_lab.SetLabel(msg)

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
        scope_tooltip.set_tooltip("指定文件名模板的生效范围\n\n目前程序支持下载的视频分为三类：投稿视频、剧集（电影、番剧等）和课程\n\n所有类型：对三种类型的视频都生效\n投稿视频\\剧集\\课程：对相应类型的视频生效\n默认：未设置相应类型的文件名模板时所使用的默认值\n\n优先级：所有类型>投稿视频=剧集=课程>默认")
        self.add_btn = wx.Button(self, -1, "添加模板", size = self.get_scaled_size((80, 24)))

        top_hbox = wx.BoxSizer(wx.HORIZONTAL)
        top_hbox.Add(template_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        top_hbox.AddStretchSpacer()
        top_hbox.Add(scope_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        top_hbox.Add(self.scope_choice, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        top_hbox.Add(scope_tooltip, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        top_hbox.Add(self.add_btn, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.template_list = wx.ListCtrl(self, -1, size = self.FromDIP((650, 220)), style = wx.LC_REPORT)

        self.auto_delete_empty_field_chk = wx.CheckBox(self, -1, "自动删除空字段")
        self.edit_btn = wx.Button(self, -1, "修改模板", size = self.get_scaled_size((80, 24)))
        self.delete_btn = wx.Button(self, -1, "删除模板", size = self.get_scaled_size((80, 24)))

        action_hbox = wx.BoxSizer(wx.HORIZONTAL)
        action_hbox.Add(self.auto_delete_empty_field_chk, 0, wx.ALL & (~wx.BOTTOM), self.FromDIP(6))
        action_hbox.AddStretchSpacer()
        action_hbox.Add(self.edit_btn, 0, wx.ALL & (~wx.BOTTOM), self.FromDIP(6))
        action_hbox.Add(self.delete_btn, 0, wx.ALL & (~wx.LEFT) & (~wx.BOTTOM), self.FromDIP(6))

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
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def Bind_EVT(self):
        self.add_btn.Bind(wx.EVT_BUTTON, self.onAddEVT)
        self.edit_btn.Bind(wx.EVT_BUTTON, self.onEditEVT)
        self.delete_btn.Bind(wx.EVT_BUTTON, self.onDeleteEVT)

    def init_utils(self):
        def init_list_column():
            self.template_list.AppendColumn("模板", width = self.FromDIP(500))
            self.template_list.AppendColumn("生效范围", width = self.FromDIP(100))

        def init_list_data():
            for entry in Config.Download.file_name_template_list:
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
        pass

    def onDeleteEVT(self, event):
        pass

    def check_existence(self, scope: str):
        for i in range(self.template_list.GetItemCount()):
            if self.template_list.GetItemText(i, 1) == scope:
                return True
            