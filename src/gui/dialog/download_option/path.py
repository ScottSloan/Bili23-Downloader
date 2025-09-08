import wx
import shutil

from utils.config import Config
from utils.common.enums import Platform
from utils.common.formatter.formatter import FormatUtils
from utils.common.const import Const
from utils.common.style.icon_v4 import Icon, IconID

from gui.dialog.setting.file_name.custom_file_name_v3 import CustomFileNameDialog

from gui.component.panel.panel import Panel
from gui.component.staticbitmap.staticbitmap import StaticBitmap

class PathStaticBox(Panel):
    def __init__(self, parent):
        Panel.__init__(self, parent)

        self.init_UI()

        self.Bind_EVT()

    def init_UI(self):
        path_box = wx.StaticBox(self, -1, "下载目录设置")

        self.path_box = wx.TextCtrl(path_box, -1)
        self.browse_btn = wx.Button(path_box, -1, "浏览", size = self.get_scaled_size((60, 24)))

        path_hbox = wx.BoxSizer(wx.HORIZONTAL)
        path_hbox.Add(self.path_box, 1, wx.ALL & (~wx.BOTTOM) | wx.ALIGN_CENTER, self.FromDIP(6))
        path_hbox.Add(self.browse_btn, 0, wx.ALL & (~wx.LEFT) & (~wx.BOTTOM) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.disk_space_lab = wx.StaticText(path_box, -1, "磁盘可用空间：计算中...")
        self.warn_icon = StaticBitmap(path_box, bmp = wx.ArtProvider().GetBitmap(wx.ART_WARNING, size = self.FromDIP((16, 16))), size = self.FromDIP((16, 16)))
        self.warn_icon.SetToolTip("当前下载目录磁盘空间不足 5 GB，可能会导致下载失败，请腾出足够的磁盘空间。")
        self.warn_icon.Hide()
        self.custom_file_name_btn = wx.Button(path_box, -1, "自定义下载文件名", size = self.get_scaled_size((120, 28)))

        info_hbox = wx.BoxSizer(wx.HORIZONTAL)
        info_hbox.Add(self.disk_space_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        info_hbox.Add(self.warn_icon, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        info_hbox.AddStretchSpacer()
        info_hbox.Add(self.custom_file_name_btn, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))

        path_sbox = wx.StaticBoxSizer(path_box, wx.VERTICAL)
        path_sbox.Add(path_hbox, 0, wx.EXPAND)
        path_sbox.Add(info_hbox, 0, wx.EXPAND)

        self.SetSizer(path_sbox)

    def Bind_EVT(self):
        self.browse_btn.Bind(wx.EVT_BUTTON, self.onBrowsePathEVT)

        self.custom_file_name_btn.Bind(wx.EVT_BUTTON, self.onCustomFileNameEVT)

    def onBrowsePathEVT(self, event):
        dlg = wx.DirDialog(self, "选择下载目录", defaultPath = self.path_box.GetValue())

        if dlg.ShowModal() == wx.ID_OK:
            self.path_box.SetValue(dlg.GetPath())

            self.update_disk_space()

    def load_data(self):
        self.update_disk_space()

        Config.Temp.file_name_template_list = Config.Download.file_name_template_list.copy()

        self.path_box.SetValue(Config.Download.path)

    def update_disk_space(self):
        match Platform(Config.Sys.platform):
            case Platform.Windows:
                path = f"{self.path_box.GetValue()[:3]}\\"

            case Platform.Linux | Platform.macOS:
                path = "/"

        total, used, free = shutil.disk_usage(path)

        free_str = FormatUtils.format_size(free)

        self.disk_space_lab.SetLabel(f"磁盘可用空间：{free_str}")

        self.check_disk_space(free)

    def check_disk_space(self, free_space: int):
        enough = free_space > 5 * Const.Size_1GB

        self.warn_icon.Show(not enough)

        self.Layout()

    def onCustomFileNameEVT(self, event: wx.CommandEvent):
        dlg = CustomFileNameDialog(self.GetParent())
        dlg.ShowModal()

    def save(self):
        Config.Download.file_name_template_list = Config.Temp.file_name_template_list.copy()

        Config.Download.path = self.path_box.GetValue()
