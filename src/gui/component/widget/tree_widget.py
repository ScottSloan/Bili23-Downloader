from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QApplication
from PySide6.QtCore import Qt, QPoint, QSize, Signal
from PySide6.QtGui import QMouseEvent

from qfluentwidgets import TreeWidget

class DragTreeWidget(TreeWidget):
    itemMoved = Signal(int, int)

    def __init__(self, parent = None):
        super().__init__(parent)

        self.setObjectName("EditDragTreeWidget")
        self.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self.setIndentation(0)

        self.item_widget_column = -1

        # 记录手动拖拽的状态
        self._is_dragging = False
        self._drag_start_pos = QPoint()
        self._current_drag_item = None

    def setColumnHeaders(self, headers: list, widths: list):
        self.setHeaderLabels(headers)

        for index, width in enumerate(widths):
            self.setColumnWidth(index, width)

    def setWidgetColumn(self, column: int):
        self.item_widget_column = column

    def add_item(self, *args):
        item = QTreeWidgetItem(*args)
        item.setSizeHint(0, QSize(0, 40))

        self.addTopLevelItem(item)

        self.scrollToBottom()
            
        return item

    def remove_item(self, item: int):
        self.takeTopLevelItem(self.indexOfTopLevelItem(item))

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
            current_row = self.indexOfTopLevelItem(self._current_drag_item)
            target_row = self.indexOfTopLevelItem(target_item)

            item = self.takeTopLevelItem(current_row)
            self.insertTopLevelItem(target_row, item)
            
            # 保持项的选中状态，并始终显示这个项
            self.setCurrentItem(item)

            # 发送信号，通知外部更新数据和重新绑定 Widget
            self.itemMoved.emit(current_row, target_row)

class ColumnTreeWidget(TreeWidget):
    def __init__(self, parent = None):
        super().__init__(parent)    

        self.setObjectName("ColumnTreeWidget")
        self.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self.setIndentation(0)

        self.tooltipEnabled = False
        
    def setColumnHeaders(self, headers: list, widths: list):
        self.setHeaderLabels(headers)

        for index, width in enumerate(widths):
            self.setColumnWidth(index, width)

    def setTooltipEnabled(self, enabled: bool):
        self.tooltipEnabled = enabled

    def addRow(self, *args, userData = None):
        item = QTreeWidgetItem([*args])
        item.setSizeHint(0, QSize(0, 40))
        self.addTopLevelItem(item)

        if self.tooltipEnabled:
            for index, text in enumerate(args):
                item.setToolTip(index, text)

        if userData is not None:
            item.setData(0, Qt.ItemDataRole.UserRole, userData)

        return item

