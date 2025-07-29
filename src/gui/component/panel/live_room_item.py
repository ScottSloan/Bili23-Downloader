import wx

from gui.component.panel.panel import Panel

class LiveRoomItemPanel(Panel):
    def __init__(self, parent):
        Panel.__init__(self, parent)

        self.init_UI()

    def init_UI(self):
        font = self.GetFont()
        font.SetFractionalPointSize(font.GetFractionalPointSize() + 2)

        self.up_name_lab = wx.StaticText(self, -1, "主播")
        self.up_name_lab.SetFont(font)

        self.title_lab = wx.StaticText(self, -1, "直播间标题")

        self.room_id_lab = wx.StaticText(self, -1, "ID 123456", size = self.FromDIP((90, 16)))
        self.status_lab = wx.StaticText(self, -1, "未录制")

        info_hbox = wx.BoxSizer(wx.HORIZONTAL)
        info_hbox.Add(self.room_id_lab, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM) | wx.ALIGN_CENTER | wx.ALIGN_LEFT, self.FromDIP(6))
        info_hbox.Add(self.status_lab, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM) | wx.ALIGN_CENTER | wx.ALIGN_LEFT, self.FromDIP(6))

        room_info_vbox = wx.BoxSizer(wx.VERTICAL)
        room_info_vbox.Add(self.up_name_lab, 0, wx.ALL & (~wx.TOP) & (~wx.BOTTOM) | wx.EXPAND, self.FromDIP(6))
        room_info_vbox.Add(self.title_lab, 0, wx.ALL & (~wx.TOP) | wx.EXPAND, self.FromDIP(6))
        room_info_vbox.Add(info_hbox, 0, wx.EXPAND)

        panel_hbox = wx.BoxSizer(wx.HORIZONTAL)
        panel_hbox.Add(room_info_vbox, 0, wx.EXPAND)

        bottom_border = wx.StaticLine(self, -1, style = wx.LI_HORIZONTAL)

        panel_vbox = wx.BoxSizer(wx.VERTICAL)
        panel_vbox.Add(panel_hbox, 1, wx.EXPAND)
        panel_vbox.Add(bottom_border, 0, wx.EXPAND)

        self.SetSizer(panel_vbox)
