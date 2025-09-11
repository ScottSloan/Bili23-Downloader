import wx

from utils.common.data.priority import video_quality_priority
from utils.common.style.icon_v4 import Icon, IconID

from gui.component.window.dialog import Dialog
from gui.component.button.bitmap_button import BitmapButton
from gui.component.misc.tooltip import ToolTip

class EditPriorityDialog(Dialog):
    def __init__(self, parent: wx.Window, category: str, priority: list):
        self.category = category
        self.priority = priority

        Dialog.__init__(self, parent, title = f"{category}优先级设置")

        self.init_UI()

        self.Bind_EVT()

        self.init_data()

        self.CenterOnParent()

    def init_UI(self):
        tip_lab = wx.StaticText(self, -1, "优先级列表")
        tooltip = ToolTip(self)
        tooltip.set_tooltip(f"列表从上到下表示优先级递减，优先级高的{self.category}将优先下载，若无可用{self.category}则依次向下查找，直到找到可用{self.category}为止。")

        top_hbox = wx.BoxSizer(wx.HORIZONTAL)
        top_hbox.Add(tip_lab, 0, wx.ALL & (~wx.BOTTOM) | wx.ALIGN_CENTER, self.FromDIP(6))
        top_hbox.Add(tooltip, 0, wx.ALL & (~wx.BOTTOM) & (~wx.LEFT) | wx.ALIGN_CENTER, self.FromDIP(6))

        self.data_list = wx.ListBox(self, -1, size = self.FromDIP((130, 210)))

        list_vbox = wx.BoxSizer(wx.VERTICAL)
        list_vbox.Add(top_hbox, 0, wx.EXPAND)
        list_vbox.Add(self.data_list, 0, wx.ALL, self.FromDIP(6))

        self.to_top_btn = BitmapButton(self, Icon.get_icon_bitmap(IconID.To_Top))
        self.to_top_btn.SetToolTip("移至顶部")
        self.up_btn = BitmapButton(self, Icon.get_icon_bitmap(IconID.Up))
        self.up_btn.SetToolTip("上移")
        self.down_btn = BitmapButton(self, Icon.get_icon_bitmap(IconID.Down))
        self.down_btn.SetToolTip("下移")
        self.to_bottom_btn = BitmapButton(self, Icon.get_icon_bitmap(IconID.To_Bottom))
        self.to_bottom_btn.SetToolTip("移至底部")
        self.reset_btn = BitmapButton(self, Icon.get_icon_bitmap(IconID.Refresh))
        self.reset_btn.SetToolTip("重置")

        action_vbox = wx.BoxSizer(wx.VERTICAL)
        action_vbox.AddStretchSpacer()
        action_vbox.Add(self.to_top_btn, 0, wx.ALL & (~wx.LEFT) & (~wx.BOTTOM), self.FromDIP(6))
        action_vbox.Add(self.up_btn, 0, wx.ALL & (~wx.LEFT) & (~wx.BOTTOM), self.FromDIP(6))
        action_vbox.Add(self.down_btn, 0, wx.ALL & (~wx.LEFT) & (~wx.BOTTOM), self.FromDIP(6))
        action_vbox.Add(self.to_bottom_btn, 0, wx.ALL & (~wx.LEFT) & (~wx.BOTTOM), self.FromDIP(6))
        action_vbox.Add(self.reset_btn, 0, wx.ALL & (~wx.LEFT), self.FromDIP(6))
        action_vbox.AddStretchSpacer()

        hbox = wx.BoxSizer(wx.HORIZONTAL)
        hbox.Add(list_vbox, 0, wx.EXPAND)
        hbox.Add(action_vbox, 0, wx.EXPAND)

        self.SetSizerAndFit(hbox)

    def Bind_EVT(self):
        self.up_btn.Bind(wx.EVT_BUTTON, self.onUpEVT)
        self.down_btn.Bind(wx.EVT_BUTTON, self.onDownEVT)

        self.to_top_btn.Bind(wx.EVT_BUTTON, self.onToTopEVT)
        self.to_bottom_btn.Bind(wx.EVT_BUTTON, self.onToBottomEVT)

    def init_data(self):
        self.data_list.Set(self.priority)

    def onUpEVT(self, event: wx.CommandEvent):
        current_item = self.data_list.GetSelection()

        self.move_to(current_item - 1)

    def onDownEVT(self, event: wx.CommandEvent):
        current_item = self.data_list.GetSelection()

        self.move_to(current_item + 1)

    def onToTopEVT(self, event: wx.CommandEvent):
        self.move_to(0)

    def onToBottomEVT(self, event: wx.CommandEvent):
        self.move_to(self.data_list.GetCount() - 1)

    def move_to(self, index: int):
        current_item = self.data_list.GetSelection()

        if index in range(0, self.data_list.GetCount()):
            string = self.data_list.GetString(current_item)

            self.data_list.Delete(current_item)
            self.data_list.Insert(string, index)

            self.data_list.SetString(index, string)

            self.data_list.SetSelection(index)
        else:
            wx.Bell()