from PySide6.QtWidgets import QListWidgetItem
from PySide6.QtCore import Qt

from qfluentwidgets import SubtitleLabel, BodyLabel

from gui.component.widget import DragListWidget
from gui.component.dialog import DialogBase

class PriorityDialog(DialogBase):
    def __init__(self, map_data: dict, config_data: list, parent = None):
        super().__init__(parent)

        self.map_data = map_data.copy()
        self.config_data = config_data.copy()

        self.init_UI()

        self.load_list_data()

    def init_UI(self):
        self.caption_lab = SubtitleLabel(self.tr("Customize Priority"), self)
        self.tip_lab = BodyLabel(self.tr("Drag items to reorder. Higher items have higher priority."))

        self.drag_list = DragListWidget(self)

        self.viewLayout.addWidget(self.caption_lab)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(self.tip_lab)
        self.viewLayout.addWidget(self.drag_list)

        self.widget.setMinimumWidth(400)
        self.widget.setMinimumHeight(475)

    def load_list_data(self):
        for config_value in self.config_data:
            item = QListWidgetItem(self.map_data[config_value])
            item.setData(Qt.ItemDataRole.UserRole, config_value)

            self.drag_list.addItem(item)

    def get_config_value(self):
        config_value = []

        for row in range(self.drag_list.count()):
            item = self.drag_list.item(row)

            config_value.append(item.data(Qt.ItemDataRole.UserRole))

        return config_value
