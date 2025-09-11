import wx

from utils.config import Config
from utils.common.enums import Platform

from gui.dialog.setting.ass_style.danmaku import DanmakuPage
from gui.dialog.setting.ass_style.subtitle import SubtitlePage

from gui.component.window.dialog import Dialog

class CustomASSStyleDialog(Dialog):
    def __init__(self, parent: wx.Window):
        Dialog.__init__(self, parent, "自定义 ASS 样式")

        self.init_UI()

        self.CenterOnParent()

    def init_UI(self):
        self.notebook = wx.Notebook(self, -1, size = self.get_book_size())

        self.notebook.AddPage(DanmakuPage(self.notebook), "弹幕")
        self.notebook.AddPage(SubtitlePage(self.notebook), "字幕")

        self.ok_btn = wx.Button(self, wx.ID_OK, "确定", size = self.get_scaled_size((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, "取消", size = self.get_scaled_size((80, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer(1)
        bottom_hbox.Add(self.ok_btn, 0, wx.ALL, self.FromDIP(6))
        bottom_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.notebook, 0, wx.ALL & (~wx.BOTTOM) | wx.EXPAND, self.FromDIP(6))
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def onOKEVT(self):
        for i in range(self.notebook.GetPageCount()):
            page, option = self.notebook.GetPage(i).get_option()

            Config.Temp.ass_style[page] = option

    def get_book_size(self):
        match Platform(Config.Sys.platform):
            case Platform.Windows:
                return self.FromDIP((350, 450))
            
            case Platform.Linux | Platform.macOS:
                return self.FromDIP((500, 570))