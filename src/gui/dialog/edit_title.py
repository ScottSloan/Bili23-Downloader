import wx

from gui.component.text_ctrl import TextCtrl
from gui.component.dialog import Dialog

class EditTitleDialog(Dialog):
    def __init__(self, parent, title: str):
        self.title = title

        Dialog.__init__(self, parent, "修改标题")

        self.init_UI()

        self.Bind_EVT()

        self.CenterOnParent()

    def init_UI(self):
        title_lab = wx.StaticText(self, -1, "请输入新标题，新标题将作为 {title} 字段")

        self.title_box = TextCtrl(self, -1, self.title, size = self.get_scaled_size((350, 24)), style = wx.TE_PROCESS_ENTER)

        self.ok_btn = wx.Button(self, wx.ID_OK, "确定", size = self.get_scaled_size((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, "取消", size = self.get_scaled_size((80, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer(1)
        bottom_hbox.Add(self.ok_btn, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        bottom_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)

        vbox.Add(title_lab, 0, wx.ALL, self.FromDIP(6))
        vbox.Add(self.title_box, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def Bind_EVT(self):
        self.ok_btn.Bind(wx.EVT_BUTTON, self.onConfirm)
        self.title_box.Bind(wx.EVT_TEXT_ENTER, self.onConfirm)

    def onConfirm(self, event):
        if not self.title_box.GetValue():
            wx.MessageDialog(self, "修改标题失败\n\n新标题不能为空", "警告", wx.ICON_WARNING).ShowModal()
            return
        
        event.Skip()
