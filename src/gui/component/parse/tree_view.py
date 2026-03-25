from PySide6.QtCore import Qt, QModelIndex

from qfluentwidgets import TreeView, RoundMenu, Action, FluentIcon, MessageBox, setCustomStyleSheet

from gui.component.parse.model import ParseModel

from util.common.icon import ExtendedFluentIcon
from util.parse.episode.tree import TreeItem

import webbrowser

class ParseTreeView(TreeView):
    def __init__(self, main_window, parent = None):
        super().__init__(parent)

        self.main_window = main_window

        self._model = ParseModel(parent = self)

        self.setModel(self._model)
        self.setUniformRowHeights(True)
        self.setAlternatingRowColors(True)
        self.setSelectionMode(TreeView.SelectionMode.SingleSelection)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        self.customContextMenuRequested.connect(self.on_context_menu)

        self.__set_QSS()
        
        self._setHeaderWidth()

    def _setHeaderWidth(self):
        self.setColumnWidth(0, 140)     # 序号列

        header = self.header()
        header.setSectionResizeMode(1, header.ResizeMode.Stretch)

    def update_tree(self, root_node: TreeItem):
        self._model.beginResetModel()
        self._model.root_node = root_node
        self._model.endResetModel()

        self.expandAll()

    def get_all_items(self):
        return self._model.root_node.get_all_children()
    
    def get_checked_items(self, to_dict = False):
        return self._model.root_node.get_all_checked_children(to_dict = to_dict)

    def get_checked_items_count(self):
        return len(self.get_checked_items())
    
    def get_total_items_count(self):
        return len(self.get_all_items())
    
    def get_first_item_info(self):
        total_items = self.get_all_items()

        return total_items[0].to_dict() if total_items else None

    def check_all_items(self, uncheck = False):
        # 只需要改变根节点的状态，子节点会自动跟随
        self._model.root_node.set_checked_state(Qt.CheckState.Unchecked if uncheck else Qt.CheckState.Checked)

        # 更新视图
        self._model.check_state_changed.emit(QModelIndex())
        self.update()

    def on_context_menu(self, pos):
        global_pos = self.viewport().mapToGlobal(pos)
        
        index = self.indexAt(pos)

        if not index.isValid():
            return
        
        item: TreeItem = index.internalPointer()

        menu = RoundMenu(parent = self)

        check_all_action = Action(
            icon = ExtendedFluentIcon.SELECT_ALL,
            text = self.tr("Deselect All") if self._model.root_node.checked == Qt.CheckState.Checked else self.tr("Select All"),
            parent = self
        )
        check_all_action.triggered.connect(lambda: self.on_check_all_items(item))
        menu.addAction(check_all_action)
        menu.addSeparator()

        toggle_action = Action(
            icon = ExtendedFluentIcon.SELECT,
            text = self.tr("Select Item") if item.checked == Qt.CheckState.Unchecked else self.tr("Deselect Item"),
            parent = self
        )
        toggle_action.triggered.connect(lambda: self.on_toggle_check_state(item))
        menu.addAction(toggle_action)

        if item.count() == 0:
            open_in_browser_action = Action(icon = FluentIcon.GLOBE, text = self.tr("Open in Browser"), parent = self)
            open_in_browser_action.triggered.connect(lambda: self.on_open_in_browser(item))
            menu.addAction(open_in_browser_action)

        view_metadata_action = Action(icon = FluentIcon.DOCUMENT, text = self.tr("View Metadata"), parent = self)
        view_metadata_action.triggered.connect(lambda: self.on_view_metadata(item))

        menu.addSeparator()
        menu.addAction(view_metadata_action)

        menu.exec(global_pos)

    def on_check_all_items(self, item: TreeItem):
        self.check_all_items(uncheck = item.checked == Qt.CheckState.Checked)

    def on_toggle_check_state(self, item: TreeItem):
        item.set_checked_state(Qt.CheckState.Checked if item.checked == Qt.CheckState.Unchecked else Qt.CheckState.Unchecked)

        self._model.check_state_changed.emit(QModelIndex())

    def on_open_in_browser(self, item: TreeItem):
        if item.url:
            webbrowser.open(item.url)

    def on_view_metadata(self, item: TreeItem):
        info = item.to_dict()

        info_str = "\n".join(f"{key}: {value}" for key, value in info.items())

        dialog = MessageBox(title = self.tr("Metadata"), content = info_str, parent = self.main_window)
        dialog.exec()

    def __set_QSS(self):
        light_style = """
            QTreeView {
                background-color: transparent;
                alternate-background-color: #f0f4f9;
            }
        """


        dark_style = """
            QTreeView {
                background-color: transparent;
                alternate-background-color: #343434;
            }
        """

        setCustomStyleSheet(self, light_style, dark_style)

    