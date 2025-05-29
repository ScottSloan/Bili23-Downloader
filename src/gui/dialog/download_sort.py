import wx

from utils.config import Config

from gui.component.dialog import Dialog

class DownloadSortDialog(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent, "下载分类设置")

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

        self.CenterOnParent()

    def init_UI(self):
        self.enable_download_sort_chk = wx.CheckBox(self, -1, "启用下载分类")

        self.sort_by_up_chk = wx.CheckBox(self, -1, "按 UP 主进行分类")
        self.sort_by_collection_chk = wx.CheckBox(self, -1, "按合集标题进行分类")
        self.sort_by_series_chk = wx.CheckBox(self, -1, "按剧集名称进行分类")

        grid_vbox = wx.FlexGridSizer(3, 2, 0, 0)
        grid_vbox.AddSpacer(self.FromDIP(20))
        grid_vbox.Add(self.sort_by_up_chk, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        grid_vbox.AddSpacer(self.FromDIP(20))
        grid_vbox.Add(self.sort_by_collection_chk, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        grid_vbox.AddSpacer(self.FromDIP(20))
        grid_vbox.Add(self.sort_by_series_chk, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))

        self.ok_btn = wx.Button(self, wx.ID_OK, "确定", size = self.get_scaled_size((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, "取消", size = self.get_scaled_size((80, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(self.ok_btn, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        bottom_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.enable_download_sort_chk, 0, wx.ALL, self.FromDIP(6))
        vbox.Add(grid_vbox, 0, wx.EXPAND)
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def Bind_EVT(self):
        self.enable_download_sort_chk.Bind(wx.EVT_CHECKBOX, self.onEnableSortEVT)

        self.sort_by_up_chk.Bind(wx.EVT_CHECKBOX, self.onEnableOKEVT)
        self.sort_by_collection_chk.Bind(wx.EVT_CHECKBOX, self.onEnableOKEVT)
        self.sort_by_series_chk.Bind(wx.EVT_CHECKBOX, self.onEnableOKEVT)

        self.ok_btn.Bind(wx.EVT_BUTTON, self.onConfirmEVT)
    
    def init_utils(self):
        self.enable_download_sort_chk.SetValue(Config.Temp.enable_download_sort)
        self.sort_by_up_chk.SetValue(Config.Temp.sort_by_up)
        self.sort_by_collection_chk.SetValue(Config.Temp.sort_by_collection)
        self.sort_by_series_chk.SetValue(Config.Temp.sort_by_series)

        self.onEnableSortEVT(0)

    def onEnableSortEVT(self, event):
        enable = self.enable_download_sort_chk.GetValue()

        self.sort_by_up_chk.Enable(enable)
        self.sort_by_collection_chk.Enable(enable)
        self.sort_by_series_chk.Enable(enable)

        self.onEnableOKEVT(event)

    def onConfirmEVT(self, event):
        Config.Temp.enable_download_sort = self.enable_download_sort_chk.GetValue()
        Config.Temp.sort_by_up = self.sort_by_up_chk.GetValue()
        Config.Temp.sort_by_collection = self.sort_by_collection_chk.GetValue()
        Config.Temp.sort_by_series = self.sort_by_series_chk.GetValue()

        event.Skip()

    def onEnableOKEVT(self, event):
        self.ok_btn.Enable(self.sort_by_up_chk.GetValue() or self.sort_by_collection_chk.GetValue() or self.sort_by_series_chk.GetValue())
