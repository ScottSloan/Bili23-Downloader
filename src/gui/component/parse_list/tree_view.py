from PySide6.QtWidgets import QHeaderView
from PySide6.QtCore import Qt, QModelIndex

from qfluentwidgets import TreeView, RoundMenu, Action, FluentIcon, MessageBox, setCustomStyleSheet

from gui.component.parse_list.model import ParseModel

from util.common import ExtendedFluentIcon, signal_bus, config
from util.parse.episode.tree import TreeItem, Attribute
from util.common.enum import ToastNotificationCategory

from typing import List
import webbrowser

class ParseTreeView(TreeView):
    def __init__(self, main_window, parent = None):
        super().__init__(parent)

        self.main_window = main_window

        self._model = ParseModel(parent = self)

        self.setModel(self._model)
        self.setUniformRowHeights(True)
        self.setAlternatingRowColors(True)
        self.setSortingEnabled(True)
        self.setSelectionMode(TreeView.SelectionMode.SingleSelection)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        self.customContextMenuRequested.connect(self.on_context_menu)
        signal_bus.parse.update_column_settings.connect(self._setHeaderWidth)

        self.__set_QSS()
        
        self._setHeaderWidth()

    def _setHeaderWidth(self):
        for index, entry in enumerate(config.get(config.parse_list_column)):
            self.setColumnWidth(index, entry["width"])

        # 重新展开
        self.expandAll()

        header = self.header()
        header.setStretchLastSection(False)

    def update_tree(self, root_node: TreeItem, current_episode_data: tuple = None):
        self._model.beginResetModel()
        self._model.root_node = root_node
        self._model.endResetModel()

        self.expandAll()

        # 根据传入的剧集数据定位到对应的项目
        self.locate_to_item_by_episode_data(current_episode_data)

    def clear_tree(self):
        invisible_root = TreeItem({"number": "", "title": ""})
        
        self.update_tree(invisible_root)

    def get_all_items(self):
        return self._model.root_node.get_all_children()
    
    def get_checked_items(self, to_dict = False, mark_as_downloaded = False):
        return self._model.root_node.get_all_checked_children(to_dict = to_dict, mark_as_downloaded = mark_as_downloaded)

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
        self.update_check_state()

    def reverse_check_state(self):
        all_items = self.get_all_items()

        for item in all_items:
            item.set_checked_state(Qt.CheckState.Checked if item.checked == Qt.CheckState.Unchecked else Qt.CheckState.Unchecked)

        self.update_check_state()

    def _create_action(self, icon, text, slot):
        action = Action(icon=icon, text=text, parent=self)
        action.triggered.connect(slot)
        return action

    def on_context_menu(self, pos):
        global_pos = self.viewport().mapToGlobal(pos)
        
        index = self.indexAt(pos)

        if not index.isValid():
            return
        
        item: TreeItem = index.internalPointer()

        menu = RoundMenu(parent=self)

        # 1. 全局选择操作
        check_all_text = self.tr("Check All") if self._model.root_node.checked == Qt.CheckState.Unchecked else self.tr("Uncheck All")
        menu.addAction(self._create_action(ExtendedFluentIcon.SELECT_ALL, check_all_text, self.on_toggle_check_all_items))
        menu.addAction(self._create_action(ExtendedFluentIcon.RETRY, self.tr("Reverse"), self.reverse_check_state))
        menu.addSeparator()

        # 2. 当前项操作
        check_item_text = self.tr("Check Item") if item.checked == Qt.CheckState.Unchecked else self.tr("Uncheck Item")
        menu.addAction(self._create_action(ExtendedFluentIcon.SELECT, check_item_text, lambda: self.on_toggle_check_state(item)))

        # 3. 叶子节点操作 (无子节点的项)
        if item.count() == 0:
            menu.addAction(self._create_action(FluentIcon.GLOBE, self.tr("Open in Browser"), lambda: self.on_open_in_browser(item)))
            menu.addAction(self._create_action(FluentIcon.DOWNLOAD, self.tr("Download as Single Video"), lambda: self.on_download_as_single_video(item)))
            menu.addAction(self._create_action(ExtendedFluentIcon.RETRY, self.tr("Update Media Info"), lambda: self.update_media_info(item.to_dict())))

        # 4. 元数据信息
        menu.addSeparator()
        menu.addAction(self._create_action(FluentIcon.DOCUMENT, self.tr("View Metadata"), lambda: self.on_view_metadata(item)))

        menu.exec(global_pos)

    def on_toggle_check_all_items(self):
        self.check_all_items(uncheck = self._model.root_node.checked != Qt.CheckState.Unchecked)

    def on_toggle_check_state(self, item: TreeItem):
        item.set_checked_state(Qt.CheckState.Checked if item.checked == Qt.CheckState.Unchecked else Qt.CheckState.Unchecked)

        self.update_check_state()

    def on_open_in_browser(self, item: TreeItem):
        if item.url:
            webbrowser.open(item.url)

    def on_view_metadata(self, item: TreeItem):
        info = item.to_dict()

        info_str = "\n".join(f"{key}: {value}" for key, value in info.items())

        dialog = MessageBox(title = self.tr("Metadata"), content = info_str, parent = self.main_window)
        dialog.exec()

    def on_download_as_single_video(self, item: TreeItem):
        item.downloaded = True

        item.set_attribute(Attribute.DOWNLOAD_AS_SINGLE_VIDEO_BIT)

        signal_bus.download.create_task.emit([item.to_dict()])

    def search_keywords(self, keywords: str = None):
        if not keywords:
            self._model.search_keyword = ""
            return
        
        self._model.search_keyword = keywords
        
        # 通知视图模型进行更新以便高亮显示
        self._model.layoutAboutToBeChanged.emit()
        self._model.layoutChanged.emit()

        self.expandAll()
            
        # 在 TreeItem 中递归处理数据层搜索
        matched_items = self._model.root_node.search_items(keywords)

        # 滚动并定位到第一个匹配的节点
        if matched_items:
            self.scroll_to_item(matched_items[0])

        return matched_items

    def scroll_to_item(self, item: TreeItem):
        index = self._model.get_index_for_item(item)

        if index.isValid():
            self.scrollTo(index)

            # 选中该项
            self.setCurrentIndex(index)

    def locate_to_item_by_episode_data(self, current_episode_data: tuple = None):
        # 没传入剧集数据，不做任何操作
        if not current_episode_data:
            return

        key = current_episode_data[0]
        value = current_episode_data[1]

        # 根据传入的剧集数据定位到对应的项目
        all_items = self.get_all_items()

        # 不仅滚动到该项，还要自动选中
        for item in all_items:
            if getattr(item, key) == value:
                self.scroll_to_item(item)
                item.set_checked_state(Qt.CheckState.Checked)
                break

    def check_items(self, items: List[TreeItem]):
        for item in items:
            item.set_checked_state(Qt.CheckState.Checked)

        self.update_check_state()

    def update_check_state(self):
        self._model.check_state_changed.emit(QModelIndex())
        self.update()

    def batch_select(self, number_list: List[int]):
        all_items = self.get_all_items()

        for item in all_items:
            if item.number in number_list:
                item.set_checked_state(Qt.CheckState.Checked)

        self.update_check_state()

    def update_media_info(self, episode_data: dict):
        signal_bus.toast.show.emit(ToastNotificationCategory.INFO, "", self.tr("Updating media info..."))

        signal_bus.parse.preview_init.emit(episode_data)

    def shift_select_range(self, new_index: QModelIndex):
        if self._model.last_changed_index.isValid():
            last_row = self._model.last_changed_index.row()
            new_row = new_index.row()

            start_row = min(last_row, new_row)
            end_row = max(last_row, new_row)

            for row in range(start_row, end_row + 1):
                index = self._model.index(row, 0)
                item: TreeItem = index.internalPointer()

                item.set_checked_state(Qt.CheckState.Checked)

            self.update_check_state()

    def mark_item_as_downloaded(self, item_list: List[TreeItem]):
        for item in item_list:
            item.downloaded = True

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
