import wx

from utils.config import Config

from gui.template import Dialog

class AboutWindow(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent, "关于", (350, 250))

        self.init_controls()

    def init_controls(self):
        logo_sbm = wx.StaticBitmap(self.panel, -1, wx.Image(Config._logo, wx.BITMAP_TYPE_PNG).ConvertToBitmap())

        font_bold = wx.Font(11, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_BOLD, False, "微软雅黑")
        name_lb = wx.StaticText(self.panel, -1, "Bilibili Video Downloader")
        name_lb.SetFont(font_bold)

        font_normal = wx.Font(10, wx.FONTFAMILY_DEFAULT, wx.FONTSTYLE_NORMAL, wx.FONTWEIGHT_NORMAL, False, "微软雅黑")
        version_lb = wx.StaticText(self.panel, -1, Config._version)
        version_lb.SetFont(font_normal)

        desc_lb = wx.StaticText(self.panel, -1, "Download bilibili videos easily.")
        desc_lb.SetFont(font_normal)

        copyright_lb = wx.StaticText(self.panel, -1, "Copyright © 2022 Scott Sloan")
        copyright_lb.SetFont(font_normal)

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(logo_sbm, 0, wx.ALL | wx.ALIGN_CENTER, 10)
        vbox.Add(name_lb, 0, wx.TOP | wx.ALIGN_CENTER, 10)
        vbox.Add(version_lb, 0, wx.TOP | wx.ALIGN_CENTER, 5)
        vbox.Add(desc_lb, 0, wx.TOP | wx.ALIGN_CENTER, 5)
        vbox.Add(copyright_lb, 0, wx.TOP | wx.ALIGN_CENTER, 5)

        self.panel.SetSizer(vbox)