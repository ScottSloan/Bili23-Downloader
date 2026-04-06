from PySide6.QtCore import Qt

from qfluentwidgets import SubtitleLabel, BodyLabel

from gui.component.widget import CheckableDragListWidget
from gui.component.dialog import DialogBase

from util.common import config, signal_bus, Translator

class ParseListColumnDialog(DialogBase):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.init_UI()

        self.init_data()

    def init_UI(self):
        self.caption_lab = SubtitleLabel(self.tr("Customize Displayed Columns"))

        column_lab = BodyLabel(self.tr("Check the columns you want to display and drag to reorder them"))

        self.drag_list = CheckableDragListWidget()

        self.viewLayout.addWidget(self.caption_lab)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(column_lab)
        self.viewLayout.addWidget(self.drag_list)

        self.widget.setMinimumWidth(350)

    def init_data(self):
        for entry in config.get(config.parse_list_column):
            column_type = entry["attr_key"]
            column_show = entry["show"]

            label = Translator.COLUMN_NAME(column_type)

            self.drag_list.addCheckableItem(label, column_show, entry)

        self.drag_list.setRowEnabled(0, False)   # 禁止隐藏第一列（序号）

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

        signal_bus.parse.update_column_settings.emit()
            
        return super().accept()
