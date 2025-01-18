import wx

from utils.config import Config
from utils.common.map import cdn_map

class ChangeCDNDialog(wx.Dialog):
    def __init__(self, parent):
        wx.Dialog.__init__(self, parent, -1, "更改 CDN")

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

        self.CenterOnParent()

    def init_UI(self):
        def _get_scale_size(_size: tuple):
            match Config.Sys.platform:
                case "windows":
                    return self.FromDIP(_size)
                
                case "linux" | "darwin":
                    return wx.DefaultSize

        self.cdn_list = wx.ListCtrl(self, -1, size = self.FromDIP((600, 250)), style = wx.LC_REPORT)

        self.ok_btn = wx.Button(self, wx.ID_OK, "确定", size = _get_scale_size((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, "取消", size = _get_scale_size((80, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer(1)
        bottom_hbox.Add(self.ok_btn, 0, wx.ALL & (~wx.TOP), 10)
        bottom_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), 10)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.cdn_list, 0, wx.ALL | wx.EXPAND, 10)
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def Bind_EVT(self):
        self.ok_btn.Bind(wx.EVT_BUTTON, self.onConfirm)

    def init_utils(self):
        self.init_listctrl()

        self.init_cdn_list()
    
    def init_listctrl(self):
        self.cdn_list.AppendColumn("序号", width = self.FromDIP(50))
        self.cdn_list.AppendColumn("CDN", width = self.FromDIP(280))
        self.cdn_list.AppendColumn("提供商", width = self.FromDIP(140))
        self.cdn_list.AppendColumn("延迟", width = self.FromDIP(100))

    def init_cdn_list(self):
        for key, value in cdn_map.items():
            self.cdn_list.Append([str(key + 1), value["cdn"], value["provider"]])

    def get_cdn(self):
        return self.cdn_list.GetItemText(self.cdn_list.GetFocusedItem(), 1)

    def onConfirm(self, event):
        if self.cdn_list.GetFocusedItem() == -1:
            wx.MessageDialog(self, "请选择 CDN\n\n请选择需要替换的 CDN", "警告", wx.ICON_WARNING).ShowModal()
            return

        event.Skip()