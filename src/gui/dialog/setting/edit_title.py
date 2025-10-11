import wx
import gettext

from gui.component.window.dialog import Dialog
from gui.component.text_ctrl.search_ctrl import SearchCtrl

_ = gettext.gettext

class EditTitleDialog(Dialog):
    def __init__(self, parent, title: str):
        self.title = title

        Dialog.__init__(self, parent, _("修改标题"))

        self.init_UI()

        self.Bind_EVT()

        self.CenterOnParent()

    def init_UI(self):
        title_lab = wx.StaticText(self, -1, _("新标题将作为 {title} 字段"))

        self.title_box = SearchCtrl(self, _("请输入新标题"), size = self.FromDIP((350, -1)), clear_btn = True)
        self.title_box.SetValue(self.title)

        self.ok_btn = wx.Button(self, wx.ID_OK, _("确定"), size = self.get_scaled_size((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, _("取消"), size = self.get_scaled_size((80, 30)))

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
        self.title_box.Bind(wx.EVT_KEY_DOWN, self.onEnterEVT)

    def onEnterEVT(self, event: wx.KeyEvent):
        keycode = event.GetKeyCode()

        if keycode in [wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER]:
            ok_event = wx.PyCommandEvent(wx.EVT_BUTTON.typeId, self.ok_btn.GetId())
            ok_event.SetEventObject(self.ok_btn)

            wx.PostEvent(self.ok_btn.GetEventHandler(), ok_event)

        event.Skip()

    def onOKEVT(self):
        if not self.title_box.GetValue():
            wx.MessageDialog(self, "修改标题失败\n\n新标题不能为空", "警告", wx.ICON_WARNING).ShowModal()
            return True
