import wx

from utils.common.style.icon_v4 import Icon, IconID
from utils.common.map import get_mapping_key_by_value

from gui.component.window.dialog import Dialog
from gui.component.button.bitmap_button import BitmapButton
from gui.component.misc.tooltip import ToolTip

class EditPriorityDialog(Dialog):
    def __init__(self, parent: wx.Window, category: str, priority_data: dict, priority_setting: list):
        self.category = category
        self.priority_data = priority_data
        self.priority_setting = priority_setting

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

        self.data_list = wx.ListCtrl(self, -1, size = self.FromDIP((180, 220)), style = wx.LC_REPORT)

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

        self.ok_btn = wx.Button(self, wx.ID_OK, "确定", size = self.get_scaled_size((80, 30)))
        self.cancel_btn = wx.Button(self, wx.ID_CANCEL, "取消", size = self.get_scaled_size((80, 30)))

        bottom_hbox = wx.BoxSizer(wx.HORIZONTAL)
        bottom_hbox.AddStretchSpacer(1)
        bottom_hbox.Add(self.ok_btn, 0, wx.ALL & (~wx.TOP), self.FromDIP(6))
        bottom_hbox.Add(self.cancel_btn, 0, wx.ALL & (~wx.TOP) & (~wx.LEFT), self.FromDIP(6))

        vbox = wx.BoxSizer(wx.VERTICAL)
        vbox.Add(hbox, 0, wx.EXPAND)
        vbox.Add(bottom_hbox, 0, wx.EXPAND)

        self.SetSizerAndFit(vbox)

    def Bind_EVT(self):
        self.up_btn.Bind(wx.EVT_BUTTON, self.onUpEVT)
        self.down_btn.Bind(wx.EVT_BUTTON, self.onDownEVT)

        self.to_top_btn.Bind(wx.EVT_BUTTON, self.onToTopEVT)
        self.to_bottom_btn.Bind(wx.EVT_BUTTON, self.onToBottomEVT)

        self.reset_btn.Bind(wx.EVT_BUTTON, self.onResetEVT)

    def init_data(self):
        self.init_list_columns()
        self.init_list_data()

    def init_list_columns(self):
        self.data_list.AppendColumn("优先级", width = self.FromDIP(45))
        self.data_list.AppendColumn(self.category, width = self.FromDIP(120))

    def init_list_data(self):
        for index, value in enumerate(self.priority_setting):
            label = get_mapping_key_by_value(self.priority_data, value)

            self.data_list.Append([str(index + 1), label])

    def onUpEVT(self, event: wx.CommandEvent):
        self.move_to(self.data_list.GetFocusedItem() - 1)

        self.update_priority()

    def onDownEVT(self, event: wx.CommandEvent):
        self.move_to(self.data_list.GetFocusedItem() + 1)

        self.update_priority()

    def onToTopEVT(self, event: wx.CommandEvent):
        self.move_to(0)

        self.update_priority()

    def onToBottomEVT(self, event: wx.CommandEvent):
        self.move_to(self.data_list.GetItemCount() - 1)

        self.update_priority()
    
    def onResetEVT(self, event: wx.CommandEvent):
        dlg = wx.MessageDialog(self, "重置优先级\n\n确定要重置优先级设置吗？", "重置", wx.YES_NO | wx.ICON_WARNING)

        if dlg.ShowModal() == wx.ID_YES:
            self.data_list.DeleteAllItems()

            self.priority_setting = list(self.priority_data.values())

            self.init_list_data()

    def move_to(self, index: int):
        current_item = self.data_list.GetFocusedItem()

        if index in range(0, self.data_list.GetItemCount()):
            label = self.data_list.GetItemText(current_item, 1)

            self.data_list.DeleteItem(current_item)
            self.data_list.InsertItem(index, "")

            self.data_list.SetItem(index, 1, label)

            self.data_list.Select(index)
            self.data_list.Focus(index)
        else:
            wx.Bell()

        self.data_list.SetFocus()

    def update_priority(self):
        for index in range(self.data_list.GetItemCount()):
            self.data_list.SetItem(index, 0, str(index + 1))

    def get_priority(self) -> dict:
        priority_list = []

        for index in range(self.data_list.GetItemCount()):
            label = self.data_list.GetItemText(index, 1)
            
            priority_list.append(self.priority_data.get(label))

        return priority_list