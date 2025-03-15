import wx

from utils.config import Config

from gui.component.text_ctrl import TextCtrl
from gui.component.dialog import Dialog

class UpdateWindow(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent, "检查更新")

        self.init_UI()

        self.Bind_EVT()

        self.CenterOnParent()

        self.showUpdateInfo()

        wx.Bell()

    def init_UI(self):
        font: wx.Font = self.GetFont()
        font.SetFractionalPointSize(int(font.GetFractionalPointSize() + 5))

        title_lab = wx.StaticText(self, -1, "有新的更新可用")
        title_lab.SetFont(font)

        self.detail_lab = wx.StaticText(self, -1, "Version 1.00，发布于 1970/1/1，大小 0MB")

        top_border = wx.StaticLine(self, -1, style = wx.HORIZONTAL)

        font: wx.Font = self.GetFont()
        font.SetFractionalPointSize(int(font.GetFractionalPointSize() + 1))

        self.changelog = TextCtrl(self, -1, size = self.FromDIP((600, 320)), style = wx.TE_MULTILINE | wx.TE_READONLY)
        self.changelog.SetFont(font)

        bottom_border = wx.StaticLine(self, -1, style = wx.HORIZONTAL)

        self.update_btn = wx.Button(self, -1, "更新", size = self.FromDIP((100, 28)))
        self.ignore_btn = wx.Button(self, wx.ID_CANCEL, "忽略", size = self.FromDIP((100, 28)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer()
        bottom_hbox.Add(self.update_btn, 0, wx.ALL, 10)
        bottom_hbox.Add(self.ignore_btn, 0, wx.ALL & (~wx.LEFT), 10)

        update_vbox = wx.BoxSizer(wx.VERTICAL)
        update_vbox.Add(title_lab, 0, wx.ALL, 10)
        update_vbox.Add(self.detail_lab, 0, wx.ALL & (~wx.TOP), 10)
        update_vbox.Add(top_border, 0, wx.EXPAND)
        update_vbox.Add(self.changelog, 1, wx.ALL | wx.EXPAND, 10)
        update_vbox.Add(bottom_border, 0, wx.EXPAND)
        update_vbox.Add(bottom_hbox, 0, wx.EXPAND, 0)

        self.SetSizerAndFit(update_vbox)

        self.set_dark_mode()
    
    def Bind_EVT(self):
        self.update_btn.Bind(wx.EVT_BUTTON, self.onUpdate)
    
    def onUpdate(self, event):
        import webbrowser

        webbrowser.open(Config.Temp.update_json["url"])

        self.Hide()

    def showUpdateInfo(self):
        data = Config.Temp.update_json

        self.SetTitle("检查更新")

        self.changelog.SetValue(data["changelog"])

        self.detail_lab.SetLabel(f"Version {data['version']}，发布于 {data['date']}，大小 {data['size']}")

        self.update_btn.Show(True)

        self.Layout()

    def set_dark_mode(self):
        super().set_dark_mode()

        self.changelog.SetBackgroundColour("white")