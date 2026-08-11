from PySide6.QtCore import Qt, QAbstractItemModel, QModelIndex, Signal
from PySide6.QtGui import QBrush, QColor

from qfluentwidgets import themeColor, isDarkTheme

from .header import StrFormatter, DurationFormatter, DateFormatter

from util.common.translator import Translator
from util.common.signal_bus import signal_bus
from util.common.config import config

from util.parse.episode.tree import TreeItem

# data() 是绘制时的最热路径，提前解引用角色常量，避免每次调用都走三层属性查找
DISPLAY_ROLE = Qt.ItemDataRole.DisplayRole
CHECK_STATE_ROLE = Qt.ItemDataRole.CheckStateRole
FOREGROUND_ROLE = Qt.ItemDataRole.ForegroundRole

class ParseModel(QAbstractItemModel):
    check_state_changed = Signal(QModelIndex)

    def __init__(self, root_node: TreeItem = None, parent = None):
        super().__init__(parent)

        if root_node is None:
            root_node = TreeItem({})

        self.root_node = root_node
        self.search_keyword = ""
        self._category_name = ""

        # 每项各列的显示文本缓存，列数据不会随勾选、排序变化，只在模型重置时失效
        self._display_cache: dict[TreeItem, list] = {}

        self._highlight_brush = None
        self._disabled_brush = None

        self._setup_column_data()

        signal_bus.parse.update_column_settings.connect(self._setup_column_data)

        self.modelReset.connect(self._display_cache.clear)
        config.themeChanged.connect(self._reset_brush_cache)
        config.themeColorChanged.connect(self._reset_brush_cache)

    @property
    def search_keyword(self):
        return self._search_keyword

    @search_keyword.setter
    def search_keyword(self, keyword: str):
        self._search_keyword = keyword or ""
        self._search_keyword_lower = self._search_keyword.lower()

    def _reset_brush_cache(self, *_):
        self._highlight_brush = None
        self._disabled_brush = None

    def _setup_column_data(self):
        self.beginResetModel()

        # 列的数量和顺序会变，旧缓存按列下标存放，必须一并作废
        self._display_cache.clear()

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

    def data(self, index: QModelIndex, role = DISPLAY_ROLE):
        # 视图每绘制一个单元格都会以近十种角色回调本方法，未命中的角色必须尽早返回，
        # 否则项目数量一多，单帧耗时就会超过 16ms，拖慢平滑滚动动画
        if role == DISPLAY_ROLE:
            if not index.isValid():
                return None

            return self._get_column_value(index.internalPointer(), index.column())

        if role == CHECK_STATE_ROLE:
            # 勾选状态只在序号列显示
            if index.column() != 0 or not index.isValid():
                return None

            return index.internalPointer().checked

        if role == FOREGROUND_ROLE:
            if not index.isValid():
                return None

            item: TreeItem = index.internalPointer()

            # 高亮搜索关键词
            if self._search_keyword_lower:
                if index.column() == 1 and self._search_keyword_lower in item.title.lower():
                    return self._get_highlight_brush()

            # 已下载的剧集、失效的剧集显示为灰色
            elif item.downloaded or item.expired:
                return self._get_disabled_brush()

        return None

    def _get_highlight_brush(self):
        if self._highlight_brush is None:
            self._highlight_brush = QBrush(themeColor())

        return self._highlight_brush

    def _get_disabled_brush(self):
        if self._disabled_brush is None:
            self._disabled_brush = QBrush(QColor(150, 150, 150)) if isDarkTheme() else QBrush(QColor(110, 110, 110))

        return self._disabled_brush

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
    
    def append_nodes(self, nodes: list) -> int:
        """
        向可见根节点追加子节点，返回插入的起始行号；没有插入任何内容时返回 -1

        必须成对发出 beginInsertRows / endInsertRows：视图缓存了自己的一份行布局，
        绕过通知直接改动底层数据会让两者脱节，视图随后就会按失效的行号访问模型
        """
        if not nodes or not self.root_node.count():
            return -1

        # root_node 是不可见的包装节点，真正显示的树根是它的第一个子节点
        parent_index = self.index(0, 0, QModelIndex())

        if not parent_index.isValid():
            return -1

        parent_item: TreeItem = parent_index.internalPointer()
        first = parent_item.count()

        self.beginInsertRows(parent_index, first, first + len(nodes) - 1)

        for node in nodes:
            parent_item.add_child(node)

        self.endInsertRows()

        return first

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

        # 排序会打乱行号，而视图的选中项、展开状态、悬浮项都以持久索引记录着旧行号。
        # 先取出这些索引对应的节点，排完序后再按节点的新行号改写回去，
        # 否则视图会拿着错位的行号访问模型
        old_indexes = self.persistentIndexList()
        old_items = [index.internalPointer() for index in old_indexes]

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

        for old_index, item in zip(old_indexes, old_items):
            if item is None:
                continue

            self.changePersistentIndex(old_index, self.createIndex(item.row(), old_index.column(), item))

        self.layoutChanged.emit()

    def flags(self, index: QModelIndex):
        if not index.isValid():
            # 无效索引代表不可见的顶层根，按 Qt 的约定只能返回 ItemIsDropEnabled 或空标志
            return Qt.ItemFlag.NoItemFlags

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

            item: TreeItem = index.internalPointer()
            item.set_checked_state(state)

            # 发出有效的 index，视图据此把该项记为 Shift 范围勾选的锚点
            self.check_state_changed.emit(index)

            return True

        return False

    def _get_column_value(self, item: TreeItem, column: int):
        # 时长、时间等列的格式化成本较高，而其数据在解析完成后不再变化，按项缓存结果
        row_cache = self._display_cache.get(item)

        if row_cache is None:
            row_cache = [None] * len(self._column_data)
            self._display_cache[item] = row_cache

        column_value = row_cache[column]

        if column_value is None:
            entry = self._column_data[column]

            column_value = str(entry["formatter"](getattr(item, entry["attr_key"], "")))
            row_cache[column] = column_value

        return column_value

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
        