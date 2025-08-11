import wx

from utils.config import Config
from utils.common.thread import Thread
from utils.common.model.data_type import LiveRoomInfo

from utils.parse.preview import LivePreview

from gui.component.panel.panel import Panel
from gui.component.window.dialog import Dialog

from gui.component.choice.choice import Choice

class DirectoryStaticBox(Panel):
    def __init__(self, parent: wx.Window):
        Panel.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

    def init_UI(self):
        dir_box = wx.StaticBox(self, -1, "工作目录设置")

        self.path_box = wx.TextCtrl(dir_box, -1)
        self.browse_btn = wx.Button(dir_box, -1, "浏览", size = self.get_scaled_size((60, 24)))

        dir_sbox = wx.StaticBoxSizer(dir_box, wx.HORIZONTAL)
        dir_sbox.Add(self.path_box, 1, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        dir_sbox.Add(self.browse_btn, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))

        self.SetSizer(dir_sbox)

    def Bind_EVT(self):
        self.browse_btn.Bind(wx.EVT_BUTTON, self.onBrowsePathEVT)

    def load_data(self):
        self.path_box.SetValue(Config.Download.path)

    def onBrowsePathEVT(self, event):
        dlg = wx.DirDialog(self, "选择下载目录", defaultPath = self.path_box.GetValue())

        if dlg.ShowModal() == wx.ID_OK:
            self.path_box.SetValue(dlg.GetPath())

class MediaInfoStaticBox(Panel):
    def __init__(self, parent: wx.Window):
        Panel.__init__(self, parent)

        self.init_UI()

    def init_UI(self):
        media_box = wx.StaticBox(self, -1, "媒体信息设置")

        protocol_lab = wx.StaticText(media_box, -1, "直播协议")
        self.protocol_choice = Choice(media_box, -1)

        quality_lab = wx.StaticText(media_box, -1, "清晰度")
        self.quality_choice = Choice(media_box, -1)

        codec_lab = wx.StaticText(media_box, -1, "编码格式")
        self.codec_chocie = Choice(media_box, -1)

        media_grid_box = wx.FlexGridSizer(3, 2, 0, 0)
        media_grid_box.Add(protocol_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        media_grid_box.Add(self.protocol_choice, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))
        media_grid_box.Add(quality_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
        media_grid_box.Add(self.quality_choice, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))
        media_grid_box.Add(codec_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
        media_grid_box.Add(self.codec_chocie, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))

        media_sbox = wx.StaticBoxSizer(media_box, wx.VERTICAL)
        media_sbox.Add(media_grid_box, 0, wx.EXPAND)

        self.SetSizer(media_sbox)

    def load_data(self, room_id: int):
        def worker():
            self.preview.get_live_stream_json()

            self.init_quality_choice()

        self.preview = LivePreview(room_id)

        Thread(target = worker).start()

    def init_quality_choice(self):
        def worker():
            self.protocol_choice.Set(["http_stream"])
            self.protocol_choice.SetSelection(0)

            self.quality_choice.SetChoices(quality_data_dict)

            self.codec_chocie.SetChoices(codec_data_dict)

        quality_data_dict = self.preview.get_quality_data_dict()
        codec_data_dict = self.preview.get_codec_data_dict()

        wx.CallAfter(worker)

    @property
    def quality_id(self):
        return self.quality_choice.GetCurrentClientData()

    @property
    def codec_id(self):
        return self.codec_chocie.GetCurrentClientData()

class SplitStaticBox(Panel):
    def __init__(self, parent: wx.Window):
        Panel.__init__(self, parent)

        self.init_UI()

    def init_UI(self):
        split_box = wx.StaticBox(self, -1, "自动分段设置")

        self.no_split_radiobtn = wx.RadioButton(split_box, -1, "不自动分段")
        self.split_by_duration_radiobtn = wx.RadioButton(split_box, -1, "按直播时长自动分段")
        self.split_by_size_radiobtn = wx.RadioButton(split_box, -1, "按文件大小自动分段")

        self.split_unit_left_lab = wx.StaticText(split_box, -1, "每")
        self.split_unit_box = wx.TextCtrl(split_box, -1, "100", size = self.FromDIP((50, 24)))
        self.split_unit_right_lab = wx.StaticText(split_box, -1, "MB 分为一段")

        split_unit_hbox = wx.BoxSizer(wx.HORIZONTAL)
        split_unit_hbox.Add(self.split_unit_left_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, self.FromDIP(6))
        split_unit_hbox.Add(self.split_unit_box, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))
        split_unit_hbox.Add(self.split_unit_right_lab, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        split_sbox = wx.StaticBoxSizer(split_box, wx.VERTICAL)
        split_sbox.Add(self.no_split_radiobtn, 0, wx.ALL, self.FromDIP(6))
        split_sbox.Add(self.split_by_duration_radiobtn, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        split_sbox.Add(self.split_by_size_radiobtn, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        split_sbox.Add(split_unit_hbox, 0, wx.EXPAND)

        self.SetSizer(split_sbox)
    
    def Bind_EVT(self):
        self.no_split_radiobtn.Bind(wx.EVT_RADIOBUTTON, self.onChangeSplitOptionEVT)
        self.split_by_duration_radiobtn.Bind(wx.EVT_RADIOBUTTON, self.onChangeSplitOptionEVT)
        self.split_by_size_radiobtn.Bind(wx.EVT_RADIOBUTTON, self.onChangeSplitOptionEVT)

    def load_data(self):
        self.no_split_radiobtn.SetValue(True)

        self.onChangeSplitOptionEVT(0)

    def onChangeSplitOptionEVT(self, event):
        no_split = self.no_split_radiobtn.GetValue()
        split_by_duration = self.split_by_duration_radiobtn.GetValue()
        split_by_size = self.split_by_size_radiobtn.GetValue()

        self.split_unit_left_lab.Enable(not no_split)
        self.split_unit_box.Enable(not no_split)
        self.split_unit_right_lab.Enable(not no_split)

        if split_by_duration:
            self.split_unit_right_lab.SetLabel("分钟 分为一段")
        
        if split_by_size:
            self.split_unit_right_lab.SetLabel("MB 分为一段")

class LiveRecordingOptionDialog(Dialog):
    def __init__(self, parent: wx.Window, room_info: LiveRoomInfo):
        self.room_info = room_info

        Dialog.__init__(self, parent, "录制选项")

        self.init_UI()

        self.init_utils()

        self.CenterOnParent()

    def init_UI(self):
        self.dir_box = DirectoryStaticBox(self)
        
        self.media_box = MediaInfoStaticBox(self)

        self.split_box = SplitStaticBox(self)

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(self.media_box, 0, wx.EXPAND | wx.ALL, self.FromDIP(6))
        hbox.Add(self.split_box, 0, wx.EXPAND | wx.ALL & (~wx.LEFT), self.FromDIP(6))

        self.ok_btn = wx.Button(self, wx.ID_OK, "确定", size = self.get_scaled_size((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, "取消", size = self.get_scaled_size((80, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(self.ok_btn, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        bottom_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.dir_box, 0, wx.ALL & (~wx.BOTTOM) | wx.EXPAND, self.FromDIP(6))
        vbox.Add(hbox, 0, wx.EXPAND)
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def init_utils(self):
        self.dir_box.load_data()
        self.media_box.load_data(self.room_info.room_id)
        self.split_box.load_data()

    def onOKEVT(self):
        if not self.dir_box.path_box.GetValue():
            wx.MessageDialog(self, "保存设置失败\n\n工作目录不能为空", "警告", wx.ICON_WARNING).Show()
            return True
        
        self.room_info.base_directory = self.dir_box.path_box.GetValue()

        self.room_info.quality = self.media_box.quality_id
        self.room_info.codec = self.media_box.codec_id
