from PySide6.QtWidgets import QAbstractItemView, QApplication
from PySide6.QtCore import Qt

from qfluentwidgets import ListWidget

class DragListWidget(ListWidget):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setFont(QApplication.font())
        self.setUniformItemSizes(True)
        self.setObjectName("DragListWidget")
