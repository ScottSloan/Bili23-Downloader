import os
import wx
import wx.lib.masked as masked

from utils.common.data_type import CutInfo, CutCallback
from utils.common.exception import GlobalExceptionInfo
from utils.module.ffmpeg import FFmpeg
from utils.tool_v2 import FileDirectoryTool

from gui.component.text_ctrl import TextCtrl
from gui.component.dialog import Dialog
from gui.dialog.error import ErrorInfoDialog

class CutClipDialog(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent, "截取片段")

        self.init_UI()

        self.Bind_EVT()

        self.CenterOnParent()

    def init_UI(self):
        input_lab = wx.StaticText(self, -1, "输入")
        self.input_box = TextCtrl(self, -1, size = self.get_scaled_size((400, -1)))
        self.input_browse_btn = wx.Button(self, -1, "浏览", size = self.get_scaled_size((60, 24)))

        input_hbox = wx.BoxSizer(wx.HORIZONTAL)
        input_hbox.Add(input_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        input_hbox.Add(self.input_box, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, 10)
        input_hbox.Add(self.input_browse_btn, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, 10)

        output_lab = wx.StaticText(self, -1, "输出")
        self.output_box = TextCtrl(self, -1, size = self.get_scaled_size((400, -1)))
        self.output_browse_btn = wx.Button(self, -1, "浏览", size = self.get_scaled_size((60, 24)))

        output_hbox = wx.BoxSizer(wx.HORIZONTAL)
        output_hbox.Add(output_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, 10)
        output_hbox.Add(self.output_box, 0, wx.ALL & (~wx.LEFT) & (~wx.TOP) | wx.ALIGN_CENTER, 10)
        output_hbox.Add(self.output_browse_btn, 0, wx.ALL & (~wx.LEFT) & (~wx.TOP) | wx.ALIGN_CENTER, 10)

        start_lab = wx.StaticText(self, -1, "开始时间")
        self.start_box = masked.TimeCtrl(self, -1, "00:00:00", size = self.get_scaled_size((100, 24)))
        self.start_box.SetOwnFont(self.GetFont())

        start_hbox = wx.BoxSizer(wx.HORIZONTAL)
        start_hbox.Add(start_lab, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        start_hbox.Add(self.start_box, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, 10)

        end_lab = wx.StaticText(self, -1, "结束时间")
        self.end_box = masked.TimeCtrl(self, -1, "00:00:10", size = self.get_scaled_size((100, 24)))
        self.end_box.SetOwnFont(self.GetFont())

        end_hbox = wx.BoxSizer(wx.HORIZONTAL)
        end_hbox.Add(end_lab, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_CENTER, 10)
        end_hbox.Add(self.end_box, 0, wx.ALL & (~wx.LEFT) & (~wx.TOP) | wx.ALIGN_CENTER, 10)

        self.open_location_btn = wx.Button(self, -1, "打开所在位置", size = self.FromDIP((100, 30)))
        self.cut_btn = wx.Button(self, -1, "开始截取", size = self.FromDIP((100, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(self.open_location_btn, 0, wx.ALL, 10)
        bottom_hbox.Add(self.cut_btn, 0, wx.ALL & (~wx.LEFT), 10)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(input_hbox, 0, wx.EXPAND)
        vbox.Add(output_hbox, 0, wx.EXPAND)
        vbox.Add(start_hbox, 0, wx.EXPAND)
        vbox.Add(end_hbox, 0, wx.EXPAND)
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def Bind_EVT(self):
        self.input_browse_btn.Bind(wx.EVT_BUTTON, self.onBrowseInputEVT)
        self.output_browse_btn.Bind(wx.EVT_BUTTON, self.onBrowseOutputEVT)

        self.open_location_btn.Bind(wx.EVT_BUTTON, self.onOpenLocationEVT)
        self.cut_btn.Bind(wx.EVT_BUTTON, self.onStartCutEVT)

    def onBrowseInputEVT(self, event):
        dlg = wx.FileDialog(self, "选择输入文件", style = wx.FD_OPEN, wildcard = "所有文件|*.*")

        if dlg.ShowModal() == wx.ID_OK:
            self.input_box.SetValue(dlg.GetPath())

        dlg.Destroy()

    def onBrowseOutputEVT(self, event):
        def get_new_file_name(_file_name: str):
            new_name = list(_file_name)
            new_name.insert(_file_name.rfind("."), "_out")

            return "".join(new_name)

        input_path = self.input_box.GetValue()
        file = get_new_file_name(os.path.basename(input_path))
    
        dlg = wx.FileDialog(self, "保存输出文件", style = wx.FD_SAVE, defaultFile = file, defaultDir = os.path.dirname(input_path), wildcard = "所有文件|*.*")

        if dlg.ShowModal() == wx.ID_OK:
            save_path = dlg.GetPath()

            if save_path == self.input_box.GetValue():
                wx.MessageDialog(self, "文件已存在\n\n无法覆盖原文件，请指定新的文件名", "警告", wx.ICON_WARNING).ShowModal()
                return
            
            self.output_box.SetValue(save_path)

        dlg.Destroy()

    def onStartCutEVT(self, event):
        def set_cut_info():
            cut_info = CutInfo()
            cut_info.input_path = self.input_box.GetValue()
            cut_info.output_path = self.output_box.GetValue()
            cut_info.start_time = self.start_box.GetValue(as_wxDateTime = True).Format("%H:%M:%S")
            cut_info.end_time = self.end_box.GetValue(as_wxDateTime = True).Format("%H:%M:%S")

            ffmpeg.set_cut_info(cut_info)

        if not self.input_box.GetValue():
            wx.MessageDialog(self, "未选择输入文件\n\n请选择输入文件", "警告", wx.ICON_WARNING).ShowModal()
            return

        if not self.output_box.GetValue():
            wx.MessageDialog(self, "未选择输出文件\n\n请选择输出文件", "警告", wx.ICON_WARNING).ShowModal()
            return

        ffmpeg = FFmpeg()

        set_cut_info()

        cut_callback = CutCallback()
        cut_callback.onSuccess = self.onCutSuccess
        cut_callback.onError = self.onCutError

        ffmpeg.cut_clip(cut_callback)
    
    def onOpenLocationEVT(self, event):
        FileDirectoryTool.open_file_location(self.output_box.GetValue())

    def onCutSuccess(self):
        def worker():
            wx.MessageDialog(self, "完成\n\n截取片段完成", "截取片段", wx.ICON_INFORMATION).ShowModal()

        wx.CallAfter(worker)

    def onCutError(self):
        def worker():
            dlg = wx.MessageDialog(self, "截取片段失败\n\n在调用 FFmpeg 截取片段时出错", "截取片段", wx.ICON_ERROR | wx.YES_NO)
            dlg.SetYesNoLabels("详细信息", "确定")

            if dlg.ShowModal() == wx.ID_YES:
                error_dlg = ErrorInfoDialog(self, GlobalExceptionInfo.info)
                error_dlg.ShowModal()

        wx.CallAfter(worker)