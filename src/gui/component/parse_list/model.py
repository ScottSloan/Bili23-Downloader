from PySide6.QtCore import Qt, QAbstractItemModel, QModelIndex, Signal, QPersistentModelIndex
from PySide6.QtGui import QBrush, QGuiApplication, QColor

from qfluentwidgets import themeColor, isDarkTheme

from .header import StrFormatter, DurationFormatter, DateFormatter

from util.common import config, signal_bus, Translator
from util.parse.episode.tree import TreeItem

class ParseModel(QAbstractItemModel):
    check_state_changed = Signal(QModelIndex)

    def __init__(self, root_node: TreeItem = None, parent = None):
        super().__init__(parent)

        if root_node is None:
            root_node = TreeItem({})

        self.root_node = root_node
        self.search_keyword = ""
        self._category_name = ""
        self.last_changed_index = QPersistentModelIndex()
        self.last_shift_index = QPersistentModelIndex()

        self._setup_column_data()

        signal_bus.parse.update_column_settings.connect(self._setup_column_data)

    def _setup_column_data(self):
        self.beginResetModel()

        column_map = [
            {
                "attr_key": "number",                            # 序号
                "formatter": StrFormatter,
            },
            {
                "attr_key": "title",                             # 标题
                "formatter": StrFormatter
            },
            {
                "attr_key": "badge",                             # 备注
                "formatter": StrFormatter
            },
            {
                "attr_key": "duration",                          # 时长
                "formatter": DurationFormatter
            },
            {
                "attr_key": "dyn_time",                          # 发布、收藏、观看时间
                "formatter": DateFormatter
            },
        ]

        column_map = {entry["attr_key"]: entry for entry in column_map}

        self._column_data = []

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
        if role == Qt.ItemDataRole.DisplayRole:
            return column_value
        
        elif role == Qt.ItemDataRole.CheckStateRole and index.column() == 0:
            return item.checked
            
        if role == Qt.ItemDataRole.ForegroundRole:
            # 高亮搜索关键词
            if self.search_keyword:
                if index.column() == 1 and self.search_keyword.lower() in item.title.lower():
                    return QBrush(themeColor())
            
            # 已下载的剧集、失效的剧集显示为灰色
            elif item.downloaded or item.expired:
                return QBrush(QColor(150, 150, 150)) if isDarkTheme() else QBrush(QColor(110, 110, 110))

        return None

    def headerData(self, section: int, orientation: Qt.Orientation, role = Qt.ItemDataRole.DisplayRole):
        if orientation == Qt.Orientation.Horizontal and role == Qt.ItemDataRole.DisplayRole:
            header_data = self._column_data[section]

            attr_key = header_data.get("attr_key", "")

            if attr_key == "dyn_time":
                attr_key = self._get_dyn_time_attr_key()
            
            return Translator.COLUMN_NAME(attr_key, self._category_name)
        
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
    
    def sort(self, column: int, order: Qt.SortOrder = Qt.SortOrder.AscendingOrder):
        if not self._column_data or column < 0 or column >= len(self._column_data):
            return

        self.layoutAboutToBeChanged.emit()

        attr_key = self._column_data[column]["attr_key"]
        reverse = (order == Qt.SortOrder.DescendingOrder)

        def _sort_recursive(node: TreeItem):
            if not node.children:
                return

            def sort_key(child: TreeItem):
                val = getattr(child, attr_key, "")
                # 将 None 转换为空字符串或其他默认值，以防比较报错
                if val is None:
                    return ""
                
                return val

            node.children.sort(key = sort_key, reverse = reverse)

            for child in node.children:
                _sort_recursive(child)

        _sort_recursive(self.root_node)

        # 排序后清空用于按住 Shift 连续勾选的记录索引，避免错乱
        self.last_changed_index = QPersistentModelIndex()
        self.last_shift_index = QPersistentModelIndex()

        self.layoutChanged.emit()

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
    
    def _set_category_name(self, name: str):
        self._category_name = name

    def _get_dyn_time_attr_key(self):
        match self._category_name:
            case "FAVORITES":
                # 收藏夹
                return "favtime"
            
            case "WATCH_LATER":
                # 稍后再看
                return "favtime"
            
            case "HISTORY":
                # 历史记录
                return "viewtime"
            
            case _:
                return "pubtime"
        