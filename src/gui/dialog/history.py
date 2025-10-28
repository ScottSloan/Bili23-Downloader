import wx
import gettext

from utils.common.datetime_util import DateTime

from gui.component.window.dialog import Dialog

_ = gettext.gettext

class HistoryDialog(Dialog):
    def __init__(self, parent: wx.Window):
        Dialog.__init__(self, parent, title = _("历史记录"))

        self.init_UI()

        self.Bind_EVT()

        self.init_utils()

        self.CenterOnParent()

    def init_UI(self):
        history_lab = wx.StaticText(self, -1, _("历史记录（双击列表项目开始解析）"))

        self.history_list = wx.ListCtrl(self, -1, size = self.FromDIP((600, 280)), style = wx.LC_REPORT)

        self.clear_btn = wx.Button(self, -1, _("清除记录"), size = self.get_scaled_size((100, 28)))

        btn_hbox = wx.BoxSizer(wx.HORIZONTAL)
        btn_hbox.AddStretchSpacer()
        btn_hbox.Add(self.clear_btn, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(history_lab, 0, wx.ALL & (~wx.BOTTOM), self.FromDIP(6))
        vbox.Add(self.history_list, 1, wx.ALL | wx.EXPAND, self.FromDIP(6))
        vbox.Add(btn_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def Bind_EVT(self):
        self.clear_btn.Bind(wx.EVT_BUTTON, self.onClearHistoryEVT)

        self.history_list.Bind(wx.EVT_LIST_ITEM_ACTIVATED, self.onActivateItemEVT)

    def init_utils(self):
        self.init_list_column()
        self.init_list_data()

    def init_list_column(self):
        self.history_list.AppendColumn(_("序号"), width = self.FromDIP(50))
        self.history_list.AppendColumn(_("时间"), width = self.FromDIP(150))
        self.history_list.AppendColumn(_("类别"), width = self.FromDIP(60))
        self.history_list.AppendColumn(_("标题"), width = self.FromDIP(250))
        self.history_list.AppendColumn(_("URL"), width = self.FromDIP(200))

    def init_list_data(self):
        history_data = self.history_object.get()

        for index, entry in enumerate(history_data):
            self.history_list.Append([str(index + 1), DateTime.time_str_from_timestamp(entry.get("time", ""), "%Y-%m-%d %H:%M:%S"), entry.get("category", ""), entry.get("title", ""), entry.get("url", "")])

        self.history_list.SetColumnWidth(4, self.FromDIP(-1))

    def onClearHistoryEVT(self, event: wx.CommandEvent):
        self.history_object.clear()

        self.history_list.DeleteAllItems()

        self.main_window.utils.update_history()

    def onActivateItemEVT(self, event: wx.ListEvent):
        url = self.history_list.GetItemText(event.GetIndex(), 1)

        self.main_window.top_box.url_box.SetValue(url)

        self.Close()

        self.main_window.onParseEVT(0)

    @property
    def main_window(self):
        from gui.window.main.main_v3 import MainWindow

        main_window: MainWindow = wx.FindWindowByName("main")

        return main_window

    @property
    def history_object(self):
        return self.main_window.history