from PySide6.QtCore import Qt, QAbstractItemModel, QModelIndex, Signal, QPersistentModelIndex
from PySide6.QtGui import QBrush, QGuiApplication

from qfluentwidgets import themeColor

from gui.component.parse.header import StrFormatter, DurationFormatter, DateFormatter

from util.parse.episode.tree import TreeItem
from util.common import config, signal_bus

class ParseModel(QAbstractItemModel):
    check_state_changed = Signal(QModelIndex)

    def __init__(self, root_node: TreeItem = None, parent = None):
        super().__init__(parent)

        if root_node is None:
            root_node = TreeItem({})

        self.root_node = root_node
        self.search_keyword = ""
        self.last_changed_index = QPersistentModelIndex()
        self.last_shift_index = QPersistentModelIndex()

        self._setup_column_data()

        signal_bus.parse.update_column_settings.connect(self._setup_column_data)

    def _setup_column_data(self):
        self.beginResetModel()

        column_map = [
            {
                "name": self.tr("Title"),
                "attr_key": "title",
                "formatter": StrFormatter
            },
            {
                "name": self.tr("Notes"),
                "attr_key": "badge",
                "formatter": StrFormatter
            },
            {
                "name": self.tr("Duration"),
                "attr_key": "duration",
                "formatter": DurationFormatter
            },
            {
                "name": self.tr("Publish Date"),
                "attr_key": "pubtime",
                "formatter": DateFormatter
            }
        ]

        column_map = {entry["attr_key"]: entry for entry in column_map}

        self._column_data = [
            {
                "name": self.tr("No."),
                "attr_key": "number",
                "formatter": StrFormatter,
            }
        ]

        for entry in config.get(config.parse_list_column):
            column_type = entry["attr_key"]
            column_show = entry["show"]

            if column_show:
                self._column_data.append(column_map.get(column_type, {}))

        self.endResetModel()

    def columnCount(self, parent = QModelIndex()):
        return len(self._column_data)
    
    def rowCount(self, parent = QModelIndex()):
        if parent.column() > 0:
            return 0

        if not parent.isValid():
            # 顶层：root 的子节点数量
            parent_item = self.root_node
        else:
            parent_item = parent.internalPointer()

        return parent_item.count()

    def data(self, index: QModelIndex, role = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return None

        item: TreeItem = index.internalPointer()

        column = index.column()

        column_value = self._get_column_value(item, column)

        # 序号列单独处理显示和勾选状态
        if index.column() == 0:
            if role == Qt.ItemDataRole.DisplayRole:
                return column_value
            
            elif role == Qt.ItemDataRole.CheckStateRole:
                return item.checked
            
        else:
            if role == Qt.ItemDataRole.DisplayRole:
                return column_value
            
        if role == Qt.ItemDataRole.ForegroundRole and self.search_keyword:
            if index.column() == 1 and self.search_keyword.lower() in item.title.lower():
                return QBrush(themeColor())

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role = Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            header_data = self._column_data[section]

            return header_data.get("name", None)
        
        return None
    
    def index(self, row: int, column: int, parent: QModelIndex = QModelIndex()):
        if not self.hasIndex(row, column, parent):
            return QModelIndex()

        parent_item = self.root_node if not parent.isValid() else parent.internalPointer()
        child_item = parent_item.child(row)

        if child_item is not None:
            return self.createIndex(row, column, child_item)
        
        return QModelIndex()
    
    def parent(self, index: QModelIndex):
        if not index.isValid():
            return QModelIndex()

        child_item: TreeItem = index.internalPointer()
        parent_item = child_item.parent

        if parent_item == self.root_node or parent_item is None:
            return QModelIndex()

        return self.createIndex(parent_item.row(), 0, parent_item)
    
    def flags(self, index: QModelIndex):
        if not index.isValid():
            return Qt.ItemFlag.ItemIsEnabled

        # 第一列可选中和可勾选，其他列仅可选中
        if index.column() == 0:
            return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsUserCheckable | Qt.ItemFlag.ItemIsSelectable
        else:
            return Qt.ItemFlag.ItemIsEnabled | Qt.ItemFlag.ItemIsSelectable

    def setData(self, index: QModelIndex, value, role = Qt.ItemDataRole.EditRole):
        if not index.isValid():
            return False

        if index.column() == 0 and role == Qt.ItemDataRole.CheckStateRole:
            state = Qt.CheckState(value) if isinstance(value, int) else value
            
            is_shift_pressed = bool(QGuiApplication.keyboardModifiers() & Qt.KeyboardModifier.ShiftModifier)
            is_shift_pressed = is_shift_pressed or getattr(self, 'shift_pressed', False) or getattr(self, 'shift_key_pressed', False)

            if is_shift_pressed and self.last_changed_index.isValid() and self.last_changed_index.parent() == index.parent():
                self._handle_shift_check_state(index, state)
            else:
                self._handle_normal_check_state(index, state)

            self._update_ancestors(index)
            self.check_state_changed.emit(index)

            return True

        return False

    def _handle_shift_check_state(self, index: QModelIndex, state: Qt.CheckState):
        parent_idx = index.parent()
        start_row_new = min(self.last_changed_index.row(), index.row())
        end_row_new = max(self.last_changed_index.row(), index.row())

        if not hasattr(self, 'last_shift_index') or not self.last_shift_index.isValid() or self.last_shift_index.parent() != parent_idx:
            self.last_shift_index = self.last_changed_index

        start_row_old = min(self.last_changed_index.row(), self.last_shift_index.row())
        end_row_old = max(self.last_changed_index.row(), self.last_shift_index.row())

        opposite_state = Qt.CheckState.Unchecked if state == Qt.CheckState.Checked else Qt.CheckState.Checked

        min_refresh_row = min(start_row_new, start_row_old)
        max_refresh_row = max(end_row_new, end_row_old)

        for row in range(min_refresh_row, max_refresh_row + 1):
            idx = self.index(row, 0, parent_idx)
            in_new = start_row_new <= row <= end_row_new
            in_old = start_row_old <= row <= end_row_old

            if in_new:
                idx.internalPointer().set_checked_state(state)
                self._update_descendants(idx)
            elif in_old:
                idx.internalPointer().set_checked_state(opposite_state)
                self._update_descendants(idx)

        self.dataChanged.emit(self.index(min_refresh_row, 0, parent_idx), self.index(max_refresh_row, 0, parent_idx))
        self.last_shift_index = QPersistentModelIndex(index)

    def _handle_normal_check_state(self, index: QModelIndex, state: Qt.CheckState):
        item: TreeItem = index.internalPointer()
        item.set_checked_state(state)

        self.last_changed_index = QPersistentModelIndex(index)
        self.last_shift_index = QPersistentModelIndex(index)

        self.dataChanged.emit(index, index)
        self._update_descendants(index)

    def _update_ancestors(self, index: QModelIndex):
        p_idx = self.parent(index)
        while p_idx.isValid():
            self.dataChanged.emit(p_idx, p_idx)
            p_idx = self.parent(p_idx)

    def _update_descendants(self, parent_idx: QModelIndex):
        """辅导方法：递归触发所有子孙节点视图的局部刷新"""
        rows = self.rowCount(parent_idx)
        if rows > 0:
            # 批量刷新该父节点下的所有子节点（第0列）
            top_left = self.index(0, 0, parent_idx)
            bottom_right = self.index(rows - 1, 0, parent_idx)
            self.dataChanged.emit(top_left, bottom_right)
            
            # 继续往下遍历更深层的子节点
            for r in range(rows):
                self._update_descendants(self.index(r, 0, parent_idx))

    def _get_column_value(self, item: TreeItem, column: int):
        attr_key = self._column_data[column]["attr_key"]
        formatter = self._column_data[column]["formatter"]
    
        return str(formatter(getattr(item, attr_key, "")))

    def get_index_for_item(self, item: TreeItem, column: int = 0) -> QModelIndex:
        if not item or item == self.root_node:
            return QModelIndex()
        
        return self.createIndex(item.row(), column, item)
