from PySide6.QtGui import QStandardItemModel, QStandardItem
from PySide6.QtWidgets import QApplication, QTreeView
from PySide6.QtCore import Qt, QModelIndex, Signal

from qfluentwidgets import TreeView, RoundMenu, Action

from util.parse.episode.tree import Attribute
from util.format import Units

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

class TreeListView(TreeView):
    item_check_state_changed = Signal()

    def __init__(self, parent = None):
        super().__init__(parent = parent)

        self.setAlternatingRowColors(True)
        self.setFont(QApplication.font())
        self.setObjectName("TreeListView")
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        self._updating = False
        self.total_count = 0

        self.init_tree_headers()

        self.customContextMenuRequested.connect(self.on_custom_context_menu)

    def init_tree_headers(self):
        self.data_model = QStandardItemModel()
        self.data_model.setColumnCount(4)
        self.data_model.setHorizontalHeaderLabels([self.tr("No."), self.tr("Title"), self.tr("Notes"), self.tr("Duration")])

        self.setModel(self.data_model)

        self.setColumnWidth(0, 140)
        self.setColumnWidth(1, 380)
        self.setColumnWidth(2, 90)
        self.setColumnWidth(3, 90)

        self.data_model.dataChanged.connect(self.on_data_changed)

    def on_data_changed(self, topLeft: QModelIndex, bottomRight: QModelIndex, roles: list[int] = ...):
        if self._updating:
            return
        
        if roles and Qt.ItemDataRole.CheckStateRole in roles:
            if topLeft.column() == 0:
                item = self.data_model.itemFromIndex(topLeft)

                self._updating = True

                self.update_children(item)
                self.update_parent(item)

                self._updating = False

                self.item_check_state_changed.emit()

    def update_children(self, parent_item: CheckableTreeItem):
        state = parent_item.checkState()

        self._recursive_set_check_state(parent_item, state)

    def _recursive_set_check_state(self, item: CheckableTreeItem, state: Qt.CheckState):
        for row in range(item.rowCount()):
            child = item.child(row, 0)

            if isinstance(child, CheckableTreeItem):
                if child.checkState() != state:
                    child.setCheckState(state)
                    self._recursive_set_check_state(child, state)

    def update_parent(self, child_item: CheckableTreeItem):
        parent = child_item.parent()

        if parent is None:
            return

        checked = 0
        unchecked = 0
        total = 0

        for row in range(parent.rowCount()):
            sibling = parent.child(row, 0)

            if isinstance(sibling, CheckableTreeItem):
                total += 1
                s_state = sibling.checkState()

                if s_state == Qt.CheckState.Checked:
                    checked += 1
                elif s_state == Qt.CheckState.Unchecked:
                    unchecked += 1

        if checked == total:
            new_state = Qt.CheckState.Checked

        elif unchecked == total:
            new_state = Qt.CheckState.Unchecked

        else:
            new_state = Qt.CheckState.PartiallyChecked

        if parent.checkState() != new_state:
            parent.setCheckState(new_state)
            self.update_parent(parent)

    def on_update_list(self, data: dict):
        def traverse_tree(data: dict, parent: QStandardItem):
            if data["attribute"] & Attribute.ITEM_NODE_BIT:
                # 判断是否为 node
                check_item = CheckableTreeItem(data["number"])

                title_item = StandardTreeItem(data["title"])
                badge_item = StandardTreeItem("")
                duration_item = StandardTreeItem("")

                parent.appendRow([check_item, title_item, badge_item, duration_item])

                for child in data.pop("children", []):
                    traverse_tree(child, check_item)

                check_item.setData(data.copy(), Qt.ItemDataRole.UserRole)

            else:
                check_item = CheckableTreeItem(str(data["number"]))
                check_item.setData(data.copy(), Qt.ItemDataRole.UserRole)

                title_item = StandardTreeItem(data["title"])
                badge_item = StandardTreeItem(data["badge"])
                duration_item = StandardTreeItem(Units.format_episode_duration(data["duration"]))

                parent.appendRow([check_item, title_item, badge_item, duration_item])

                self.total_count += 1

        # 直接 new 一个 model 来替换原 model
        self.init_tree_headers()

        parent = self.data_model.invisibleRootItem()

        self.data_model.removeRows(0, self.data_model.rowCount())
        self.total_count = 0

        traverse_tree(data, parent)

        self.expandAll()
        #self.adjust_column_widths()

    def check_all_items(self):
        # 选中根项目即可选中所有项目
        root = self.data_model.invisibleRootItem()

        root.child(0, 0).setCheckState(Qt.CheckState.Checked)

    def get_checked_items_count(self):
        def traverse_and_count(item: QStandardItem) -> int:
            count = 0

            for row in range(item.rowCount()):
                child = item.child(row, 0)

                data = child.data(Qt.ItemDataRole.UserRole)

                if (data["attribute"] & Attribute.ITEM_NODE_BIT == 0) and child.checkState() == Qt.CheckState.Checked:
                    # 判断是否为 item
                    count += 1

                count += traverse_and_count(child)

            return count

        root = self.data_model.invisibleRootItem()

        return traverse_and_count(root)
    
    def adjust_column_widths(self):
        self.resizeColumnToContents(0)

        self.setColumnWidth(0, self.columnWidth(0) + 20)
    
    def on_custom_context_menu(self, pos):
        global_pos = self.viewport().mapToGlobal(pos)
        
        index = self.indexAt(pos)

        if not index.isValid():
            return
                
        item = self.data_model.index(index.row(), 0, index.parent())

        menu = RoundMenu(parent = self)

        view_metadata_action = Action(self.tr("查看元数据"), self)
        view_metadata_action.triggered.connect(lambda: print(item.data(Qt.ItemDataRole.UserRole)))

        menu.addAction(view_metadata_action)

        menu.exec(global_pos)

    def get_first_episode_info(self):
        def traverse(item: QStandardItem):
            for row in range(item.rowCount()):
                child = item.child(row, 0)

                data = child.data(Qt.ItemDataRole.UserRole)

                if data["attribute"] & Attribute.ITEM_NODE_BIT == 0:
                    # 判断是否为 item
                    return data

                result = traverse(child)

                if result is not None:
                    return result
            
            return None

        root = self.data_model.invisibleRootItem()

        return traverse(root)

    def get_all_checked_episodes_info(self) -> list[dict]:
        checked_episodes = []

        def traverse(item: QStandardItem):
            for row in range(item.rowCount()):
                child = item.child(row, 0)
                data = child.data(Qt.ItemDataRole.UserRole)
                current_attribute = data["attribute"]

                if (current_attribute & Attribute.ITEM_NODE_BIT) == 0:
                    # 判断是否为 item
                    if child.checkState() == Qt.CheckState.Checked:
                        checked_episodes.append(data)

                traverse(child)

        root = self.data_model.invisibleRootItem()

        traverse(root)

        return checked_episodes

class CheckListView(TreeView):
    def __init__(self, parent = None):
        super().__init__(parent)

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

        for index, width in enumerate(widths):
            self.setColumnWidth(index, width)

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
