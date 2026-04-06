from PySide6.QtWidgets import QAbstractItemView, QApplication, QListWidgetItem
from PySide6.QtCore import Qt, QPoint
from PySide6.QtGui import QMouseEvent

from qfluentwidgets import ListWidget

class CheckableItem(QListWidgetItem):
    def __init__(self, text: str, parent = None):
        super().__init__(text, parent)

        self.setFlags(self.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        self.setCheckState(Qt.CheckState.Unchecked)

class DragListWidget(ListWidget):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        self.setFont(QApplication.font())
        self.setUniformItemSizes(True)
        self.setObjectName("DragListWidget")

        # 记录手动拖拽的状态
        self._is_dragging = False
        self._drag_start_pos = QPoint()
        self._current_drag_item = None

    def mousePressEvent(self, event: QMouseEvent):
        super().mousePressEvent(event)

        if event.button() == Qt.MouseButton.LeftButton:
            item = self.itemAt(event.pos())

            if item:
                self._is_dragging = True
                self._drag_start_pos = event.pos()
                self._current_drag_item = item

    def mouseMoveEvent(self, event: QMouseEvent):
        if not self._is_dragging or not self._current_drag_item:
            super().mouseMoveEvent(event)
            return

        if not (event.buttons() & Qt.MouseButton.LeftButton):
            super().mouseMoveEvent(event)
            return

        # 如果移动距离不够，不触发交换动作
        if (event.pos() - self._drag_start_pos).manhattanLength() < QApplication.startDragDistance():
            return

        target_item = self.itemAt(event.pos())
        # 如果鼠标移动到了另一个项目的范围内，进行动态交换
        if target_item and target_item is not self._current_drag_item:
            self.delegate.setHoverRow(-1)
            self.delegate.setPressedRow(-1)

            current_row = self.row(self._current_drag_item)
            target_row = self.row(target_item)
            
            # 取出原项目并重新插入到目标位置
            item = self.takeItem(current_row)
            self.insertItem(target_row, item)
            
            # 保持项的选中状态，并始终显示这个项
            self.setCurrentItem(item)

    def mouseReleaseEvent(self, event: QMouseEvent):
        super().mouseReleaseEvent(event)
        
        self._is_dragging = False
        self._current_drag_item = None
        self._drag_start_pos = QPoint()

class CheckableDragListWidget(DragListWidget):
    def __init__(self, parent = None):
        super().__init__(parent)

    def addCheckableItem(self, text: str, checked = False, data = None):
        item = CheckableItem(text)

        if data:
            item.setData(Qt.ItemDataRole.UserRole, data)

        if checked:
            item.setCheckState(Qt.CheckState.Checked)
            
        self.addItem(item)

    def setRowEnabled(self, row: int, enable: bool):
        item = self.item(row)

        if not item:
            return
        
        if enable:
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEnabled)
        else:
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEnabled)
