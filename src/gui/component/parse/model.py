from PySide6.QtCore import Qt, QAbstractItemModel, QModelIndex, Signal

from gui.component.parse.header import StrFormatter, DurationFormatter

from util.parse.episode.tree import TreeItem

class ParseModel(QAbstractItemModel):
    check_state_changed = Signal(QModelIndex)

    def __init__(self, root_node: TreeItem = None, parent = None):
        super().__init__(parent)

        if root_node is None:
            root_node = TreeItem({})

        self.root_node = root_node

        self._setup_column_data()

    def _setup_column_data(self):
        self._column_data = [
            {
                "name": self.tr("No."),
                "attr_key": "number",
                "formatter": StrFormatter,
            },
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
            }
        ]

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

        item: TreeItem = index.internalPointer()

        if index.column() == 0 and role == Qt.ItemDataRole.CheckStateRole:
            # 兼容处理 PySide 传递的 value 类型可能为 int 的情况
            state = Qt.CheckState(value) if isinstance(value, int) else value
            
            # 委托给 Item 自身处理内聚的级联更新逻辑，消除模型层原本暴力的外部编排
            item.set_checked_state(state)

            # --- 局部刷新 ---
            # 1. 刷新当前自身节点
            self.dataChanged.emit(index, index)

            # 2. 向上递归：局部刷新所有祖先节点
            p_idx = self.parent(index)

            while p_idx.isValid():
                self.dataChanged.emit(p_idx, p_idx)
                p_idx = self.parent(p_idx)

            # 3. 向下递归：局部刷新所有子孙节点
            self._update_descendants(index)

            self.check_state_changed.emit(index)

            return True

        return False

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