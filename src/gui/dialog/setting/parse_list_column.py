from PySide6.QtCore import Qt

from qfluentwidgets import SubtitleLabel, BodyLabel

from gui.component.widget import CheckableDragListWidget
from gui.component.dialog import DialogBase

from util.common.config import config

class ParseListColumnDialog(DialogBase):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.init_UI()

        self.init_data()

    def init_UI(self):
        self.caption_lab = SubtitleLabel(self.tr("自定义解析列表列"))

        column_lab = BodyLabel(self.tr("勾选需要显示的列，拖拽调整列顺序"))

        self.drag_list = CheckableDragListWidget()

        self.viewLayout.addWidget(self.caption_lab)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(column_lab)
        self.viewLayout.addWidget(self.drag_list)

        self.widget.setMinimumWidth(350)

    def init_data(self):
        column_map = {
            "title": self.tr("Title"),
            "badge": self.tr("Notes"),
            "duration": self.tr("Duration"),
            "pubtime": self.tr("Publish Date")
        }

        for entry in config.get(config.parse_list_column):
            column_type = entry["attr_key"]
            column_show = entry["show"]

            label = column_map.get(column_type)

            self.drag_list.addCheckableItem(label, column_show, column_type)

    def accept(self):
        column_list = []

        for row in range(self.drag_list.count()):
            item = self.drag_list.item(row)

            entry = {
                "attr_key": item.data(Qt.ItemDataRole.UserRole),
                "show": item.checkState() == Qt.CheckState.Checked
            }

            column_list.append(entry)

        if not column_list:
            return
        
        config.set(config.parse_list_column, column_list)
            
        return super().accept()
