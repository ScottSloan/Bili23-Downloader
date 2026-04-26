from PySide6.QtCore import Qt

from qfluentwidgets import SubtitleLabel, BodyLabel, SwitchButton

from gui.component.widget import CheckableDragListWidget
from gui.component.dialog import DialogBase

from util.common import config, signal_bus, Translator

class ParseListSettingsDialog(DialogBase):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.init_UI()

        self.init_data()

    def init_UI(self):
        self.caption_lab = SubtitleLabel(self.tr("Parse List Settings"), self)

        column_lab = BodyLabel(self.tr("Select columns to display and drag to reorder"), self)

        self.drag_list = CheckableDragListWidget(self)

        auto_check_all_lab = BodyLabel(self.tr("Automatically check all parsed items"), self)
        self.auto_check_all_switch = SwitchButton(self)

        self.viewLayout.addWidget(self.caption_lab)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(column_lab)
        self.viewLayout.addWidget(self.drag_list)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(auto_check_all_lab)
        self.viewLayout.addWidget(self.auto_check_all_switch)

        self.widget.setMinimumWidth(400)

    def init_data(self):
        for entry in config.get(config.parse_list_column):
            column_type = entry["attr_key"]
            column_show = entry["show"]

            label = Translator.COLUMN_NAME(column_type)

            self.drag_list.addCheckableItem(label, column_show, entry)

        self.drag_list.setRowEnabled(0, False)   # 禁止隐藏第一列（序号）
        self.drag_list.setMinDragRow(1)          # 保持第一列（序号）在最前面，不允许拖动到其他位置

    def accept(self):
        column_list = []

        for row in range(self.drag_list.count()):
            item = self.drag_list.item(row)

            entry = item.data(Qt.ItemDataRole.UserRole)

            entry["show"] = item.checkState() == Qt.CheckState.Checked

            column_list.append(entry)

        if not column_list:
            return
        
        config.set(config.parse_list_column, column_list)
        config.set(config.auto_check_all, self.auto_check_all_switch.isChecked())

        signal_bus.parse.update_column_settings.emit()
            
        return super().accept()
