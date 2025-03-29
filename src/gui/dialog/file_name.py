import wx
import re
from datetime import datetime

from utils.common.data_type import DownloadTaskInfo
from utils.common.file_name import FileNameManager

from gui.component.text_ctrl import TextCtrl
from gui.component.dialog import Dialog

class CustomFileNameDialog(Dialog):
    def __init__(self, parent, template: str, date_format: str, time_format: str, auto_adjust: bool):
        self.template = template
        self.date_format = date_format
        self.time_format = time_format
        self.auto_adjust = auto_adjust

        Dialog.__init__(self, parent, "自定义下载文件名")

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

        self.CenterOnParent()

    def init_UI(self):
        template_lab = wx.StaticText(self, -1, "文件名模板")
        self.template_box = TextCtrl(self, -1, size = self.FromDIP((550, 24)))

        template_hbox = wx.BoxSizer(wx.HORIZONTAL)
        template_hbox.Add(template_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        template_hbox.Add(self.template_box, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.error_lab = wx.StaticText(self, -1)
        self.error_lab.SetForegroundColour(wx.Colour(250, 42, 45))

        error_hbox = wx.BoxSizer(wx.HORIZONTAL)
        error_hbox.AddSpacer(template_lab.GetSize()[0] + self.FromDIP(20))
        error_hbox.Add(self.error_lab, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM) & (~wx.LEFT), self.FromDIP(6))

        self.preview_lab = wx.StaticText(self, -1, "预览：")

        fields_lab = wx.StaticText(self, -1, "可用字段列表（双击添加字段）")
        self.fields_list = wx.ListCtrl(self, -1, style = wx.LC_REPORT)
        
        fields_vbox = wx.BoxSizer(wx.VERTICAL)
        fields_vbox.Add(fields_lab, 0, wx.ALL & (~wx.BOTTOM), self.FromDIP(6))
        fields_vbox.Add(self.fields_list, 0, wx.ALL & (~wx.BOTTOM) | wx.EXPAND, self.FromDIP(6))

        date_format_lab = wx.StaticText(self, -1, "日期格式")
        self.date_format_box = TextCtrl(self, -1, self.date_format, size = self.FromDIP((150, 24)))

        time_format_lab = wx.StaticText(self, -1, "时间格式")
        self.time_format_box = TextCtrl(self, -1, self.time_format, size = self.FromDIP((150, 24)))

        self.auto_adjust_chk = wx.CheckBox(self, -1, "自动调整空字段前后的显示效果")
        self.auto_adjust_chk.SetValue(self.auto_adjust)

        datetime_hbox = wx.BoxSizer(wx.HORIZONTAL)
        datetime_hbox.Add(date_format_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        datetime_hbox.Add(self.date_format_box, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        datetime_hbox.Add(time_format_lab, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        datetime_hbox.Add(self.time_format_box, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.ok_btn = wx.Button(self, wx.ID_OK, "确定", size = self.FromDIP((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, "取消", size = self.FromDIP((80, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer(1)
        bottom_hbox.Add(self.ok_btn, 0, wx.ALL, self.FromDIP(6))
        bottom_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(template_hbox, 0, wx.EXPAND)
        vbox.Add(error_hbox, 0, wx.EXPAND)
        vbox.Add(self.preview_lab, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        vbox.Add(fields_vbox, 0, wx.EXPAND)
        vbox.Add(datetime_hbox, 0, wx.EXPAND)
        vbox.Add(self.auto_adjust_chk, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM), self.FromDIP(6))
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def Bind_EVT(self):
        self.template_box.Bind(wx.EVT_TEXT, self.onTemplateTextEVT)
        self.date_format_box.Bind(wx.EVT_TEXT, self.onDateTextEVT)
        self.time_format_box.Bind(wx.EVT_TEXT, self.onTimeTextEVT)

        self.fields_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.onAddFieldEVT)
        self.auto_adjust_chk.Bind(wx.EVT_CHECKBOX, self.onAutoAdjustEVT)

    def init_utils(self):
        def init_fields_list_column():
            self.fields_list.AppendColumn("字段名称", width = self.FromDIP(133))
            self.fields_list.AppendColumn("说明", width = self.FromDIP(233))
            self.fields_list.AppendColumn("示例", width = self.FromDIP(200))
        
        def init_field_list_content():
            content = [
                {
                    "name": "{date}",
                    "description": "日期",
                    "example": datetime.now().strftime(self.date_format_box.GetValue())
                },
                {
                    "name": "{time}",
                    "description": "时间",
                    "example": datetime.now().strftime(self.time_format_box.GetValue())
                },
                {
                    "name": "{timestamp}",
                    "description": "时间戳",
                    "example": str(int(datetime.now().timestamp()))
                },
                {
                    "name": "{pubdate}",
                    "description": "视频发布日期",
                    "example": datetime.fromtimestamp(1667061000).strftime(self.date_format_box.GetValue())
                },
                {
                    "name": "{pubtime}",
                    "description": "视频发布时间",
                    "example": datetime.fromtimestamp(1667061000).strftime(self.time_format_box.GetValue())
                },
                {
                    "name": "{pubtimestamp}",
                    "description": "视频发布时间戳",
                    "example": "1667061000"
                },
                {
                    "name": "{number}",
                    "description": "从 1 开始的序号",
                    "example": "1"
                },
                {
                    "name": "{number_with_zero}",
                    "description": "从 1 开始的序号，在前方自动补零",
                    "example": "01、001"
                },
                {
                    "name": "{tname}",
                    "description": "分区（仅投稿视频有效）",
                    "example": "综合"
                },
                {
                    "name": "{tname_v2}",
                    "description": "分区 v2（仅投稿视频有效）",
                    "example": "动漫剪辑"
                },
                {
                    "name": "{area}",
                    "description": "地区（仅剧集类视频有效）",
                    "example": "中国大陆"
                },
                {
                    "name": "{title}",
                    "description": "视频标题",
                    "example": "《孤独摇滚》第1话 孤独的转机"
                },
                {
                    "name": "{aid}",
                    "description": "视频 av 号",
                    "example": "944573356"
                },
                {
                    "name": "{bvid}",
                    "description": "视频 BV 号",
                    "example": "BV1yW4y1j7Ft"
                },
                {
                    "name": "{cid}",
                    "description": "视频 cid 号",
                    "example": "875212290"
                },
                {
                    "name": "{video_quality}",
                    "description": "视频清晰度",
                    "example": "超清 4K"
                },
                {
                    "name": "{audio_quality}",
                    "description": "音质",
                    "example": "Hi-Res 无损"
                },
                {
                    "name": "{video_codec}",
                    "description": "视频编码",
                    "example": "H265"
                },
                {
                    "name": "{duration}",
                    "description": "视频时长，单位为秒",
                    "example": "256"
                },
                {
                    "name": "{up_name}",
                    "description": "UP 主名称",
                    "example": "哔哩哔哩番剧"
                },
                {
                    "name": "{up_mid}",
                    "description": "UP 主 mid",
                    "example": "928123"
                }
            ]

            for entry in content:
                self.fields_list.Append([entry["name"], entry["description"], entry["example"]])

        init_fields_list_column()

        init_field_list_content()

        self.template_box.SetValue(self.template)

    def show_preview_file_name(self):
        if self.check_legal(self.template_box.GetValue()):
            raise NameError("template")
        
        if self.check_legal(self.date_format_box.GetValue()):
            raise NameError("date")
        
        if self.check_legal(self.time_format_box.GetValue()):
            raise NameError("time")
        
        task_info = DownloadTaskInfo()
        task_info.number = 0
        task_info.number_with_zero = "01"
        task_info.title = "《孤独摇滚》第1话 孤独的转机"
        task_info.aid = 944573356
        task_info.bvid = "BV1yW4y1j7Ft"
        task_info.cid = 875212290
        task_info.video_quality_id = 120
        task_info.audio_quality_id = 30251
        task_info.video_codec_id = 12
        task_info.duration = 256
        task_info.pubtime = 1667061000
        task_info.area = "中国大陆"
        task_info.tname_info = {
            "tname": "综合",
            "tname_v2": "动漫剪辑"
        }
        task_info.up_info = {
            "up_name": "哔哩哔哩番剧",
            "up_mid": 928123
        }

        file_name_mgr = FileNameManager(task_info)
        preview = file_name_mgr.get_full_file_name(self.template_box.GetValue(), self.auto_adjust_chk.GetValue())

        if len(preview) > 255:
            raise ValueError("max length")
        
        self.preview_lab.SetLabel(f"预览：{preview}")

    def onTemplateTextEVT(self, event):
        try:
            self.show_preview_file_name()

            self.error_lab.SetLabel("")

            self.ok_btn.Enable(True)

        except Exception as e:
            self.syntax_error(e)

        event.Skip()

    def onDateTextEVT(self, event):
        self.onTemplateTextEVT(event)

        self.fields_list.SetItem(0, 2, datetime.now().strftime(self.date_format_box.GetValue()))

        event.Skip()

    def onTimeTextEVT(self, event):
        self.onTemplateTextEVT(event)

        self.fields_list.SetItem(1, 2, datetime.now().strftime(self.time_format_box.GetValue()))

        event.Skip()

    def onAddFieldEVT(self, event):
        field_name = self.fields_list.GetItemText(self.fields_list.GetFocusedItem(), 0)

        self.template_box.AppendText(field_name)        

    def onAutoAdjustEVT(self, event):
        self.onTemplateTextEVT(event)

    def check_legal(self, file_name):
        forbidden_chars = r'[<>:"/\\|?*\x00-\x1F]'

        if re.search(forbidden_chars, file_name):
            return True
        else:
            return False

    def syntax_error(self, e):
        match e:
            case KeyError() | IndexError():
                info = "字段名无效"

            case NameError():
                match str(e):
                    case "template":
                        info = '文件名不得包含 < > : " / \\ | ? * 之中任何一个字符'
                    
                    case "date":
                        info = '日期格式错误，不得包含 < > : " / \\ | ? * 之中任何一个字符'
                    
                    case "time":
                        info = '时间格式错误，不得包含 < > : " / \\ | ? * 之中任何一个字符'
                    
                    case _:
                        info = str(e)

            case ValueError():
                match str(e):
                    case "Single '{' encountered in format string" | "expected '}' before end of string":
                        info = "字段名必须以 {} 包裹"
                    
                    case "Invalid format string":
                        info = "日期时间格式无效"

                    case "max length":
                        info = "文件名长度超过 255"

                    case _:
                        info = str(e)
            
            case _:
                info = str(e)
        
        self.error_lab.SetLabel(info)

        self.preview_lab.SetLabel("预览：-")

        self.ok_btn.Enable(False)