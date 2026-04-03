from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QApplication
from PySide6.QtCore import Qt, QPoint, QSize
from PySide6.QtGui import QMouseEvent

from qfluentwidgets import TreeWidget, TreeItemDelegate, LineEdit

class EditItemDelegate(TreeItemDelegate):
    """
    自定义委托，确保使用 Fluent 风格的编辑框样式
    """
    def createEditor(self, parent, option, index):
        # 使用 Fluent 风格编辑框
        editor = LineEdit(parent)

        return editor
    
    def updateEditorGeometry(self, editor: LineEdit, option, index):
        rect = option.rect

        # 默认弹出的位置偏下，因此向上移动 rect
        rect.moveTop(rect.top() - 2)

        editor.setGeometry(rect)

class EditDragTreeWidget(TreeWidget):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.editable_columns = []
        self.reorder_enabled = False

        self.setObjectName("EditDragTreeWidget")
        self.setItemDelegate(EditItemDelegate(self))
        self.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self.setIndentation(0)

        # 记录手动拖拽的状态
        self._is_dragging = False
        self._drag_start_pos = QPoint()
        self._current_drag_item = None

        self.itemDoubleClicked.connect(self.on_item_double_clicked)

    def setColumnEditable(self, column: int, state: bool):
        """
        设置列表指定列是否可编辑
        """
        if state and column not in self.editable_columns:
            self.editable_columns.append(column)

        if not state and column in self.editable_columns:
            self.editable_columns.remove(column)

    def setReorderEnabled(self, state: bool):
        """
        设置在列表项目发生变化时，自动更新序号列（第一列）
        """
        self.reorder_enabled = state

    def on_item_double_clicked(self, item: QTreeWidgetItem, column: int):
        if column in self.editable_columns:
            item.setFlags(item.flags() | Qt.ItemFlag.ItemIsEditable)
        else:
            item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsEditable)

    def reorder_list(self):
        for index in range(self.topLevelItemCount()):
            item = self.topLevelItem(index)
            item.setText(0, str(index + 1))

    def add_item(self, *args, edit_column = None):
        item = QTreeWidgetItem(*args)
        item.setFlags(item.flags() & ~Qt.ItemFlag.ItemIsDropEnabled | Qt.ItemFlag.ItemIsEditable)

        self.addTopLevelItem(item)

        self.scrollToBottom()

        if edit_column:
            self.editItem(item, edit_column)
            
        return item

    def remove_item(self, item: int):
        self.takeTopLevelItem(self.indexOfTopLevelItem(item))

        if self.reorder_enabled:
            self.reorder_list()

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
            
            # 取出原项目并重新插入到目标位置
            item = self.takeTopLevelItem(current_row)
            self.insertTopLevelItem(target_row, item)
            
            # 保持项的选中状态，并始终显示这个项
            self.setCurrentItem(item)

    def mouseReleaseEvent(self, event: QMouseEvent):
        super().mouseReleaseEvent(event)
        
        self._is_dragging = False
        self._current_drag_item = None
        self._drag_start_pos = QPoint()

        if self.reorder_enabled:
            self.reorder_list()

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

