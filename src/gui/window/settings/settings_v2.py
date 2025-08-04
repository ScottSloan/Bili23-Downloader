import wx

from utils.config import Config
from utils.common.enums import Platform

from gui.window.settings.basic import BasicPage
from gui.window.settings.download import DownloadPage
from gui.window.settings.advanced import AdvancedPage

from gui.component.window.dialog import Dialog

class SettingWindow(Dialog):
    def __init__(self, parent: wx.Window):
        Dialog.__init__(self, parent, "设置")

        self.init_UI()

        self.CenterOnParent()

    def init_UI(self):
        self.note = wx.Notebook(self, -1, size = self.get_book_size())

        self.note.AddPage(BasicPage(self.note), "基本")
        self.note.AddPage(DownloadPage(self.note), "下载")
        self.note.AddPage(AdvancedPage(self.note), "高级")

        self.ok_btn = wx.Button(self, wx.ID_OK, "确定", size = self.get_scaled_size((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, "取消", size = self.get_scaled_size((80, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer(1)
        bottom_hbox.Add(self.ok_btn, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        bottom_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.note, 0, wx.EXPAND | wx.ALL, self.FromDIP(6))
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def onOKEVT(self):
        return super().onOKEVT()
    
    def get_book_size(self):
        match Platform(Config.Sys.platform):
            case Platform.Windows:
                return self.FromDIP((315, 400))
            
            case Platform.Linux | Platform.macOS:
                return self.FromDIP((360, 470))
