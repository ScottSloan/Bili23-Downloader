import wx

from utils.tools import get_all_ffmpeg_path

class DetectDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, "自动检测")

        self.init_UI()

        self.Bind_EVT()

        self.CenterOnParent()

        self.init_utils()

    def init_UI(self):
        select_lab = wx.StaticText(self, -1, "请选择 FFmpeg 路径")

        self.env_chk = wx.RadioButton(self, -1, "环境变量")
        self.env_path_lab = wx.StaticText(self, -1, "未检测到 FFmpeg", size = self.FromDIP((250, 20)), style = wx.ST_ELLIPSIZE_END)

        self.cwd_chk = wx.RadioButton(self, -1, "运行目录")
        self.cwd_path_lab = wx.StaticText(self, -1, "未检测到 FFmpeg", size = self.FromDIP((250, 20)), style = wx.ST_ELLIPSIZE_END)

        self.env_chk.Enable(False)
        self.env_path_lab.Enable(False)
        self.cwd_chk.Enable(False)
        self.cwd_path_lab.Enable(False)

        self.ok_btn = wx.Button(self, wx.ID_OK, "确定", size = self.FromDIP((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, "取消", size = self.FromDIP((80, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer(1)
        bottom_hbox.Add(self.ok_btn, 0, wx.ALL & (~wx.TOP), 10)
        bottom_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), 10)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(select_lab, 0, wx.ALL, 10)
        vbox.Add(self.env_chk, 0, wx.ALL, 10)
        vbox.Add(self.env_path_lab, 0, wx.ALL & (~wx.TOP), 10)
        vbox.Add(self.cwd_chk, 0, wx.ALL & (~wx.TOP), 10)
        vbox.Add(self.cwd_path_lab, 0, wx.ALL & (~wx.TOP), 10)
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def init_utils(self):
        paths = get_all_ffmpeg_path()

        if paths["env_path"]:
            self.env_chk.Enable(True)
            self.env_path_lab.Enable(True)

            self.env_path_lab.SetLabel(paths["env_path"])
            self.env_path_lab.SetToolTip(paths["env_path"])

        if paths["cwd_path"]:
            self.cwd_chk.Enable(True)
            self.cwd_path_lab.Enable(True)
            
            self.cwd_path_lab.SetLabel(paths["cwd_path"])
            self.cwd_path_lab.SetToolTip(paths["cwd_path"])

    def Bind_EVT(self):
        self.ok_btn.Bind(wx.EVT_BUTTON, self.onConfirm)

    def onConfirm(self, event):
        if self.env_chk.GetValue() or self.cwd_chk.GetValue():
            event.Skip()
        else:
            wx.MessageDialog(self, "未选择路径\n\n请从下方选择 FFmpeg 路径", "警告", style = wx.ICON_WARNING).ShowModal()

    def getPath(self):
        if self.env_chk.GetValue():
            return self.env_path_lab.GetLabel()

        if self.cwd_chk.GetValue():
            return self.cwd_path_lab.GetLabel()
