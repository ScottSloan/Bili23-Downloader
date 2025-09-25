import wx

from gui.component.window.dialog import Dialog
from gui.component.text_ctrl.search_ctrl import SearchCtrl
from gui.component.misc.tooltip import ToolTip

class SelectBatchDialog(Dialog):
    def __init__(self, parent: wx.Window):
        from gui.window.main.main_v3 import MainWindow

        self.parent: MainWindow = parent

        Dialog.__init__(self, parent, "批量选取项目")

        self.init_UI()

        self.Bind_EVT()

        self.CenterOnParent()

    def init_UI(self):
        title_lab = wx.StaticText(self, -1, "序号区间")
        tooltip = ToolTip(self)
        tooltip.set_tooltip("序号区间支持输入多个，以英文逗号分隔，如 1-3,5,7-10 表示选取第 1 至 3 项、第 5 项和第 7 至 10 项")

        top_hbox = wx.BoxSizer(wx.HORIZONTAL)
        top_hbox.Add(title_lab, 0, wx.ALL | wx.ALIGN_CENTER, self.FromDIP(6))
        top_hbox.Add(tooltip, 0, wx.ALL & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.range_box = SearchCtrl(self, "请输入序号区间，以英文逗号分隔", size = self.FromDIP((350, -1)), clear_btn = True)

        shift_tip = wx.StaticText(self, -1, "提示：按住 Shift 键也可批量选取项目")

        self.ok_btn = wx.Button(self, wx.ID_OK, "确定", size = self.get_scaled_size((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, "取消", size = self.get_scaled_size((80, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer(1)
        bottom_hbox.Add(self.ok_btn, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        bottom_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)

        vbox.Add(top_hbox, 0, wx.EXPAND)
        vbox.Add(self.range_box, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))
        vbox.Add(shift_tip, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def Bind_EVT(self):
        self.range_box.Bind(wx.EVT_KEY_DOWN, self.onEnterEVT)

    def onEnterEVT(self, event: wx.KeyEvent):
        keycode = event.GetKeyCode()

        if keycode in [wx.WXK_RETURN, wx.WXK_NUMPAD_ENTER]:
            ok_event = wx.PyCommandEvent(wx.EVT_BUTTON.typeId, self.ok_btn.GetId())
            ok_event.SetEventObject(self.ok_btn)

            wx.PostEvent(self.ok_btn.GetEventHandler(), ok_event)

        event.Skip()

    def onOKEVT(self):
        if not self.range_box.GetValue():
            wx.MessageDialog(self, "选取剧集失败\n\n序号区间不能为空", "警告", wx.ICON_WARNING).ShowModal()
            return True
        
        self.parent.episode_list.UnCheckAllItems()
        
        self.parse_range()
        
    def parse_range(self):
        range_text = self.range_box.GetValue()

        for entry in range_text.split(","):
            if "-" in entry:
                start, end = entry.split("-")
            else:
                start, end = entry, entry

            self.parent.episode_list.CheckItemRange(int(start), int(end), uncheck_all = False)