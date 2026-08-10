from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtWidgets import QApplication, QTreeView
from PySide6.QtCore import Qt, QEvent

from qfluentwidgets import TreeView

from gui.component.widget.smooth_scroll import applySmoothScroll

class CheckableTreeItem(QStandardItem):
    def __init__(self, text: str = ""):
        super().__init__(text)

        self.setFlags(self.flags() | Qt.ItemFlag.ItemIsUserCheckable)
        self.setCheckState(Qt.CheckState.Unchecked)
        self.setEditable(False)

    def isChecked(self):
        return self.checkState() == Qt.CheckState.Checked

class StandardTreeItem(QStandardItem):
    def __init__(self, text: str = ""):
        super().__init__(text)

        self.setEditable(False)

class CheckListView(TreeView):
    def __init__(self, parent = None):
        super().__init__(parent)

        applySmoothScroll(self)

        # Shift 范围勾选：锚点为上一次手动勾选的行号
        self._check_anchor_row = -1
        # 本次 Shift 会话中被改动过的行及其原始状态，用于回拖缩小范围时还原
        self._shift_snapshot = {}
        self._applying_shift = False

        self.setObjectName("CheckListView")
        self.setFont(QApplication.font())
        self.setSelectionMode(QTreeView.SelectionMode.SingleSelection)
        self.setUniformRowHeights(True)
        self.setRootIsDecorated(False)

    def setColumnHeaders(self, headers: list, widths: list):
        self.data_model = QStandardItemModel()
        self.data_model.setColumnCount(len(headers))
        self.data_model.setHorizontalHeaderLabels(headers)

        self.setModel(self.data_model)

        self._resetCheckAnchor()

        self.data_model.itemChanged.connect(self._onItemChanged)
        self.data_model.modelReset.connect(self._resetCheckAnchor)
        self.data_model.rowsRemoved.connect(self._resetCheckAnchor)

        for index, width in enumerate(widths):
            self.setColumnWidth(index, width)

    def _resetCheckAnchor(self, *_):
        self._check_anchor_row = -1
        self._shift_snapshot.clear()

    def _onItemChanged(self, item: QStandardItem):
        # 批量应用范围时不改动锚点，否则连续 Shift 点击会不断把锚点挪到上一次的终点
        if self._applying_shift:
            return

        # 用户手动勾选了某一行，将其记为新的锚点并结束上一次 Shift 会话
        self._check_anchor_row = item.row()
        self._shift_snapshot.clear()

    def viewportEvent(self, event: QEvent):
        # Shift + 左键点击行的任意位置即可范围勾选，不必命中复选框
        if (event.type() == QEvent.Type.MouseButtonPress
                and event.button() == Qt.MouseButton.LeftButton
                and event.modifiers() & Qt.KeyboardModifier.ShiftModifier):
            index = self.indexAt(event.position().toPoint())

            # 处理成功则完整消费事件，避免再触发复选框切换和选中态变更
            if index.isValid() and self._applyShiftRange(index.row()):
                return True

        return super().viewportEvent(event)

    def _applyShiftRange(self, target_row: int):
        """以锚点的勾选状态填充锚点到目标行之间的范围，返回是否已处理"""
        model = getattr(self, "data_model", None)

        if model is None or not 0 <= self._check_anchor_row < model.rowCount():
            return False

        anchor_item = model.item(self._check_anchor_row)

        if anchor_item is None:
            return False

        # 范围统一采用锚点的状态
        state = anchor_item.checkState()

        start_row = min(self._check_anchor_row, target_row)
        end_row = max(self._check_anchor_row, target_row)
        rows = set(range(start_row, end_row + 1))

        # 批量期间屏蔽信号，避免每改一行都通知外部重新统计
        self._applying_shift = True
        model.blockSignals(True)

        # 还原本次会话中已移出范围的行
        for row in [row for row in self._shift_snapshot if row not in rows]:
            item = model.item(row)
            original = self._shift_snapshot.pop(row)

            if item is not None:
                item.setCheckState(original)

        # 应用到范围内的行，首次覆盖时记录原始状态
        for row in rows:
            item = model.item(row)

            if item is None:
                continue

            if row not in self._shift_snapshot:
                self._shift_snapshot[row] = item.checkState()

            item.setCheckState(state)

        model.blockSignals(False)

        self.setCurrentIndex(model.index(target_row, 0))
        self.viewport().update()

        # 信号被屏蔽期间外部收不到通知，这里统一补发一次
        model.itemChanged.emit(anchor_item)

        self._applying_shift = False

        return True

    def appendCheckableRow(self, *args, data = None, checked = False):
        root = self.data_model.invisibleRootItem()

        items = []

        for index, text in enumerate(args):
            if index == 0:
                item = CheckableTreeItem(text)
                item.setCheckState(Qt.CheckState.Checked if checked else Qt.CheckState.Unchecked)
            else:
                item = StandardTreeItem(text)

            if data:
                item.setData(data, Qt.ItemDataRole.UserRole)

            items.append(item)

        root.appendRow(items)

    def getCheckedItemsData(self):
        data = []

        for i in range(self.data_model.rowCount()):
            item: CheckableTreeItem = self.data_model.item(i)

            if item.isChecked():
                data.append(item.data(Qt.ItemDataRole.UserRole))

        return data

    def getCheckedItemsCount(self):
        count = 0

        for i in range(self.data_model.rowCount()):
            item: CheckableTreeItem = self.data_model.item(i)

            if item.isChecked():
                count += 1

        return count

    def setCheckStateForAll(self, state: Qt.CheckState):
        for i in range(self.data_model.rowCount()):
            item: CheckableTreeItem = self.data_model.item(i)
            item.setCheckState(state)

    def checkAll(self):
        self.setCheckStateForAll(Qt.CheckState.Checked)

    def uncheckAll(self):
        self.setCheckStateForAll(Qt.CheckState.Unchecked)
        