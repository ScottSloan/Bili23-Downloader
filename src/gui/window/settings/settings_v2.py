import wx
import gettext

from utils.config import Config
from utils.common.enums import Platform
from utils.common.exception import GlobalException, show_error_message_dialog

from gui.window.settings.basic import BasicPage
from gui.window.settings.download import DownloadPage
from gui.window.settings.advanced import AdvancedPage
from gui.window.settings.ffmpeg import FFmpegPage
from gui.window.settings.proxy import ProxyPage
from gui.window.settings.misc import MiscPage

from gui.component.window.dialog import Dialog

_ = gettext.gettext

class SettingWindow(Dialog):
    def __init__(self, parent: wx.Window):
        Dialog.__init__(self, parent, _("设置"))

        self.init_UI()

        self.CenterOnParent()

    def init_UI(self):
        self.note = wx.Notebook(self, -1, size = self.get_book_size())

        self.note.AddPage(BasicPage(self.note), _("基本"))
        self.note.AddPage(DownloadPage(self.note), _("下载"))
        self.note.AddPage(AdvancedPage(self.note), _("高级"))
        self.note.AddPage(FFmpegPage(self.note), "FFmpeg")
        self.note.AddPage(ProxyPage(self.note), _("代理"))
        self.note.AddPage(MiscPage(self.note), _("其他"))

        self.ok_btn = wx.Button(self, wx.ID_OK, _("确定"), size = self.get_scaled_size((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, _("取消"), size = self.get_scaled_size((80, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer(1)
        bottom_hbox.Add(self.ok_btn, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        bottom_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(self.note, 0, wx.EXPAND | wx.ALL, self.FromDIP(6))
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def onOKEVT(self):
        def on_error():
            show_error_message_dialog(_("保存失败"), parent = self)

        try:
            for i in range(0, self.note.GetPageCount()):
                if self.note.GetPage(i).onValidate():
                    return True
                
            Config.save_app_config()

        except Exception as e:
            raise GlobalException(callback = on_error) from e
        
    def get_book_size(self):
        match Platform(Config.Sys.platform):
            case Platform.Windows:
                if Config.Basic.language == "zh_CN":
                    return self.FromDIP((315, 450))
                else:
                    return self.FromDIP((450, 400))
            
            case Platform.Linux | Platform.macOS:
                return self.FromDIP((360, 470))
