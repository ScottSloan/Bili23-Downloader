from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem
from PySide6.QtCore import Qt

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
        self.setDragDropMode(QTreeWidget.DragDropMode.InternalMove)
        self.setDefaultDropAction(Qt.DropAction.MoveAction)
        self.setIndentation(0)

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

    def dropEvent(self, event):
        current_item = self.currentItem()

        super().dropEvent(event)

        if self.reorder_enabled:
            self.reorder_list()

        self.setCurrentItem(current_item)

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

class ColumnTreeWidget(TreeWidget):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.setObjectName("ColumnTreeWidget")
        self.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self.setIndentation(0)
        
    def setColumnHeaders(self, headers: list, widths: list):
        self.setHeaderLabels(headers)

        for index, width in enumerate(widths):
            self.setColumnWidth(index, width)

    def add_item(self, *args):
        item = QTreeWidgetItem([*args])
        self.addTopLevelItem(item)

        for index, text in enumerate(args):
            item.setToolTip(index, text)
