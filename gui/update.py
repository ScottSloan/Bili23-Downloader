import wx

class UpdateWindow(wx.Dialog):
    def __init__(self, parent, update_json):
        self.json = update_json

        wx.Dialog.__init__(self, parent, -1)

        self.init_UI()

        self.Bind_EVT()

        self.CenterOnParent()

        wx.Bell()

    def init_UI(self):
        self.icon = wx.StaticBitmap(self, -1)
        self.icon.Show(False)

        self.title_lab = wx.StaticText(self, -1)

        title_hbox = wx.BoxSizer(wx.HORIZONTAL)
        title_hbox.Add(self.icon, 0, wx.ALL, 10)
        title_hbox.Add(self.title_lab, 0, wx.ALL | wx.CENTER, 10)

        self.changelog_box = wx.TextCtrl(self, -1, self.json["changelog"], size = self.FromDIP((500, 320)), style = wx.TE_MULTILINE | wx.TE_READONLY)

        self.update_btn = wx.Button(self, -1, "更新", size = self.FromDIP((80, 25)))
        self.update_btn.Show(False)

        update_vbox = wx.BoxSizer(wx.VERTICAL)
        update_vbox.Add(title_hbox, 0, wx.EXPAND)
        update_vbox.Add(self.changelog_box, 1, wx.ALL & (~wx.TOP), 10)
        update_vbox.Add(self.update_btn, 0, wx.ALL & (~wx.TOP) | wx.ALIGN_RIGHT, 10)

        self.SetSizerAndFit(update_vbox)
    
    def Bind_EVT(self):
        self.update_btn.Bind(wx.EVT_BUTTON, self.onUpdate)
    
    def onUpdate(self, event):
        import webbrowser

        webbrowser.open(self.json["url"])

        self.Hide()

    def ui_update(self):
        self.SetTitle("检查更新")

        self.icon.SetBitmap(wx.ArtProvider.GetBitmap(wx.ART_INFORMATION, size = (48, 48)))
        self.icon.Show(True)

        self.title_lab.SetLabel(f"Version {self.json['version']} 更新可用\n\n发布时间：{self.json['date']}")

        self.update_btn.Show(True)

        self.Layout()

    def ui_changelog(self):
        self.SetTitle("更新日志")

        self.title_lab.SetLabel(f"当前版本更新日志")