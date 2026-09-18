from PySide6.QtWidgets import QTreeWidget, QTreeWidgetItem, QApplication
from PySide6.QtCore import Qt, QPoint, QSize, Signal
from PySide6.QtGui import QMouseEvent

from qfluentwidgets import TreeWidget

class DragReorderMixin:
    """
    按住左键拖动列表项换位

    抽成混入而不是让 ColumnTreeWidget 继承 DragTreeWidget：两者是平级的
    TreeWidget 子类，前者还被变量表、解析历史共用，把拖拽塞给所有使用方的
    副作用面太大。

    itemMoved 由各个宿主类自己声明 —— Signal 要定义在直接继承 QObject 的类里，
    混入类不满足这个前提。
    """

    def _init_drag(self):
        # 记录手动拖拽的状态
        self._is_dragging = False
        self._drag_start_pos = QPoint()
        self._current_drag_item = None

        self._drag_enabled = True

    def set_drag_enabled(self, enabled: bool):
        """
        开关拖拽

        列表被筛选时**必须**关掉：换位信号带的是行号，而隐藏的行不参与视觉顺序，
        两者一旦错位，落回数据的顺序就是错的
        """
        self._drag_enabled = enabled

    def mousePressEvent(self, event: QMouseEvent):
        super().mousePressEvent(event)
        if event.button() == Qt.MouseButton.LeftButton and self._drag_enabled:
            item = self.itemAt(event.pos())

            # 先判断 item 是否禁用，如果禁用则不允许拖动
            if item and not item.isDisabled():
                self._is_dragging = True
                self._drag_start_pos = event.pos()
                self._current_drag_item = item

    def mouseMoveEvent(self, event: QMouseEvent):
        if not self._drag_enabled or not self._is_dragging or not self._current_drag_item:
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

            # 换位与改选中期间必须屏蔽信号：调用方这时还没拿到新的行序，
            # 此刻若发出 currentItemChanged，它按的仍是旧行号 —— 会写到别的数据上
            blocked = self.blockSignals(True)

            try:
                item = self.takeTopLevelItem(current_row)
                self.insertTopLevelItem(target_row, item)

                # 保持项的选中状态，并始终显示这个项
                self.setCurrentItem(item)

            finally:
                self.blockSignals(blocked)

            # 发送信号，通知外部更新数据和重新绑定 Widget
            self.itemMoved.emit(current_row, target_row)

class DragTreeWidget(DragReorderMixin, TreeWidget):
    itemMoved = Signal(int, int)

    def __init__(self, parent = None):
        super().__init__(parent)

        self.setObjectName("EditDragTreeWidget")
        self.setSelectionMode(QTreeWidget.SelectionMode.SingleSelection)
        self.setIndentation(0)

        self.item_widget_column = -1

        self._init_drag()

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

    def updateGeometries(self):
        super().updateGeometries()

        self.verticalScrollBar().setSingleStep(30)

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
                item.setToolTip(index, str(text))

        if userData is not None:
            item.setData(0, Qt.ItemDataRole.UserRole, userData)

        return item
    
    def updateGeometries(self):
        super().updateGeometries()

        self.verticalScrollBar().setSingleStep(20)

class DragColumnTreeWidget(DragReorderMixin, ColumnTreeWidget):
    """带拖拽换位的 ColumnTreeWidget。顺序会被写回配置，所以只给顺序有意义的场合用"""

    itemMoved = Signal(int, int)

    def __init__(self, parent = None):
        super().__init__(parent)

        self._init_drag()

