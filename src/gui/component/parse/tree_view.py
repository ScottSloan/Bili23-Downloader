from PySide6.QtCore import Qt

from qfluentwidgets import TreeView, RoundMenu, Action, setCustomStyleSheet

from gui.component.parse.model import ParseModel

from util.parse.episode.tree import TreeItem

class ParseTreeView(TreeView):
    def __init__(self, parent = None):
        super().__init__(parent)

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
        #self.setColumnWidth(1, 380)     # 标题列

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

    def check_all_items(self):
        # 只需要改变根节点的状态，子节点会自动跟随
        self._model.root_node.set_checked_state(Qt.CheckState.Checked)

    def on_context_menu(self, pos):
        global_pos = self.viewport().mapToGlobal(pos)
        
        index = self.indexAt(pos)

        if not index.isValid():
            return
        
        item: TreeItem = index.internalPointer()

        menu = RoundMenu(parent = self)

        view_metadata_action = Action(self.tr("查看元数据"), self)
        view_metadata_action.triggered.connect(lambda: print(item.to_dict()))

        menu.addAction(view_metadata_action)

        menu.exec(global_pos)

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
