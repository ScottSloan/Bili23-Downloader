import wx

from utils.config import Config

from gui.component.text_ctrl import TextCtrl

class EditTitleDialog(wx.Dialog):
    def __init__(self, parent, title: str):
        self.title = title

        wx.Dialog.__init__(self, parent, -1, "修改标题")

        self.init_UI()

        self.Bind_EVT()

        self.CenterOnParent()

    def init_UI(self):
        def _get_scale_size(_size: tuple):
            match Config.Sys.platform:
                case "windows":
                    return self.FromDIP(_size)
                
                case "linux" | "darwin":
                    return wx.DefaultSize

        title_lab = wx.StaticText(self, -1, "请输入新标题")

        self.title_box = TextCtrl(self, -1, self.title, size = _get_scale_size((350, 24)), style = wx.TE_PROCESS_ENTER)

        self.ok_btn = wx.Button(self, wx.ID_OK, "确定", size = _get_scale_size((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, "取消", size = _get_scale_size((80, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer(1)
        bottom_hbox.Add(self.ok_btn, 0, wx.ALL & (~wx.TOP), 10)
        bottom_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), 10)

        vbox = wx.BoxSizer(wx.VERTICAL)

        vbox.Add(title_lab, 0, wx.ALL, 10)
        vbox.Add(self.title_box, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, 10)
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
