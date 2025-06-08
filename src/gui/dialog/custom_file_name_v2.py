import wx

from gui.component.dialog import Dialog

class AddNewTemplateDialog(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent, "添加文件名模板")

        self.init_UI()

        self.CenterOnParent()

    def init_UI(self):
        pass

class CustomFileNameDialog(Dialog):
    def __init__(self, parent):
        Dialog.__init__(self, parent, "自定义下载文件名")

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

        self.CenterOnParent()

    def init_UI(self):
        template_lab = wx.StaticText(self, -1, "已添加的文件名模板")

        scope_lab = wx.StaticText(self, -1, "生效范围")
        self.scope_choice = wx.Choice(self, -1)
        self.add_btn = wx.Button(self, -1, "添加", size = self.get_scaled_size((60, 24)))

        top_hbox = wx.BoxSizer(wx.HORIZONTAL)
        top_hbox.Add(template_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        top_hbox.AddStretchSpacer()
        top_hbox.Add(scope_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        top_hbox.Add(self.scope_choice, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))
        top_hbox.Add(self.add_btn, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.template_list = wx.ListCtrl(self, -1, size = self.FromDIP((600, 200)), style = wx.LC_REPORT)

        self.edit_btn = wx.Button(self, -1, "修改", size = self.get_scaled_size((60, 24)))
        self.delete_btn = wx.Button(self, -1, "删除", size = self.get_scaled_size((60, 24)))

        action_hbox = wx.BoxSizer(wx.HORIZONTAL)
        action_hbox.AddStretchSpacer()
        action_hbox.Add(self.edit_btn, 0, wx.ALL & (~wx.BOTTOM), self.FromDIP(6))
        action_hbox.Add(self.delete_btn, 0, wx.ALL & (~wx.LEFT) & (~wx.BOTTOM), self.FromDIP(6))

        self.ok_btn = wx.Button(self, wx.ID_OK, "确定", size = self.FromDIP((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, "取消", size = self.FromDIP((80, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer(1)
        bottom_hbox.Add(self.ok_btn, 0, wx.ALL, self.FromDIP(6))
        bottom_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(top_hbox, 0, wx.EXPAND)
        vbox.Add(self.template_list, 1, wx.ALL & (~wx.TOP) & (~wx.BOTTOM) | wx.EXPAND, self.FromDIP(6))
        vbox.Add(action_hbox, 0, wx.EXPAND)
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def Bind_EVT(self):
        self.add_btn.Bind(wx.EVT_BUTTON, self.onAddEVT)
        self.edit_btn.Bind(wx.EVT_BUTTON, self.onEditEVT)
        self.delete_btn.Bind(wx.EVT_BUTTON, self.onDeleteEVT)

    def init_utils(self):
        def init_list():
            self.template_list.AppendColumn("模板", width = self.FromDIP(450))
            self.template_list.AppendColumn("生效范围", width = self.FromDIP(100))

        init_list()

    def onAddEVT(self, event):
        dlg = AddNewTemplateDialog(self)
        dlg.ShowModal()

    def onEditEVT(self, event):
        pass

    def onDeleteEVT(self, event):
        pass