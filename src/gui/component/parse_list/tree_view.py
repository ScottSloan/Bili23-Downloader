from PySide6.QtWidgets import QApplication
from PySide6.QtCore import Qt, QModelIndex, QTimer

from qfluentwidgets import TreeView, RoundMenu, Action, FluentIcon, isDarkTheme, setCustomStyleSheet

from .model import ParseModel

from util.common.enum import ToastNotificationCategory
from util.common.icon import ExtendedFluentIcon
from util.common.signal_bus import signal_bus
from util.common.config import config

from util.parse.episode.tree import TreeItem, Attribute

from typing import List
from collections import deque
import webbrowser

class ParseTreeView(TreeView):
    def __init__(self, main_window, parent = None):
        super().__init__(parent)

        self.main_window = main_window

        self._model = ParseModel(parent = self)
        self._expand_timer = QTimer(self)
        self._expand_timer.setSingleShot(True)
        self._expand_timer.timeout.connect(self._expand_next_batch)
        self._expand_queue = deque()
        self._expand_callback = None
        self._expand_batch_size = 100

        self.setModel(self._model)
        self.setUniformRowHeights(True)
        self.setSortingEnabled(True)
        self.setSelectionMode(TreeView.SelectionMode.SingleSelection)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        self.customContextMenuRequested.connect(self.on_context_menu)
        signal_bus.parse.update_column_settings.connect(self._setHeaderWidth)
        
        self._setHeaderWidth()
        self.update_alternate_row_color()

    def _setHeaderWidth(self):
        for index, entry in enumerate(config.get(config.parse_list_column)):
            self.setColumnWidth(index, entry["width"])

        # 重新展开
        self._schedule_expand_all()

        header = self.header()
        header.setStretchLastSection(False)

    def update_tree(self, root_node: TreeItem, current_episode_data: tuple = None):
        self._model.beginResetModel()
        self._model.root_node = root_node
        self._model.endResetModel()

        target_item = self.locate_to_item_by_episode_data(
            current_episode_data,
            scroll = False
        )

        self._schedule_expand_all(
            lambda: self.scroll_to_item(target_item) if target_item else None
        )

    def _schedule_expand_all(self, callback = None):
        self._expand_queue.clear()
        self._expand_queue.append((QModelIndex(), 0))
        self._expand_callback = callback

        if not self._expand_timer.isActive():
            self._expand_timer.start(0)

    def _expand_next_batch(self):
        processed = 0

        while self._expand_queue and processed < self._expand_batch_size:
            parent, start_row = self._expand_queue.popleft()
            rows = self._model.rowCount(parent)

            for row in range(start_row, rows):
                index = self._model.index(row, 0, parent)
                if not index.isValid():
                    continue

                self.expand(index)
                self._expand_queue.append((index, 0))
                processed += 1

                if processed >= self._expand_batch_size:
                    if row + 1 < rows:
                        self._expand_queue.appendleft((parent, row + 1))
                    break

        if self._expand_queue:
            self._expand_timer.start(0)
            return

        callback = self._expand_callback
        self._expand_callback = None

        if callback:
            callback()

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
            menu.addAction(self._create_action(ExtendedFluentIcon.RETRY, self.tr("Update Media Info"), lambda: self.on_update_media_info(item.to_dict())))

        # 4. 元数据信息
        menu.addSeparator()
        menu.addAction(self._create_action(FluentIcon.DOCUMENT, self.tr("View Metadata"), lambda: self.on_view_metadata(item)))

        if item.count() == 0:
            menu.addAction(self._create_action(FluentIcon.PHOTO, self.tr("View Cover"), lambda: self.on_view_cover(item)))

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
        def on_copy_metadata(info_str):
            clipboard = QApplication.clipboard()
            clipboard.setText(info_str)

        from ..dialog import MessageBox

        info = item.to_dict()

        info_str = "\n".join(f"{key}: {value}" for key, value in info.items())

        dialog = MessageBox(title = self.tr("Metadata"), content = info_str, parent = self.main_window)

        dialog.cancelButton.setText(self.tr("Copy"))
        dialog.cancelButton.clicked.disconnect()
        dialog.cancelButton.clicked.connect(lambda: on_copy_metadata(info_str))

        dialog.exec()

    def on_download_as_single_video(self, item: TreeItem):
        item.downloaded = True

        item.set_attribute(Attribute.DOWNLOAD_AS_SINGLE_VIDEO_BIT)

        signal_bus.download.create_task.emit([item.to_dict()], True)

    def search_keywords(self, keywords: str = None):
        if not keywords:
            self._model.search_keyword = ""
            return
        
        self._model.search_keyword = keywords
        
        # 通知视图模型进行更新以便高亮显示
        self._model.layoutAboutToBeChanged.emit()
        self._model.layoutChanged.emit()

        matched_items = self._model.root_node.search_items(keywords)

        self._schedule_expand_all(
            lambda: self.scroll_to_item(matched_items[0])
            if matched_items else None
        )

        # 滚动并定位到第一个匹配的节点
        return matched_items

    def scroll_to_item(self, item: TreeItem):
        index = self._model.get_index_for_item(item)

        if index.isValid():
            self.scrollTo(index)

            # 选中该项
            self.setCurrentIndex(index)

    def locate_to_item_by_episode_data(self, current_episode_data: tuple = None, scroll = True):
        # 没传入剧集数据，不做任何操作
        if not current_episode_data:
            return None

        key = current_episode_data[0]
        value = current_episode_data[1]

        # 根据传入的剧集数据定位到对应的项目
        all_items = self.get_all_items()

        # 不仅滚动到该项，还要自动选中
        for item in all_items:
            if getattr(item, key) == value:
                item.set_checked_state(Qt.CheckState.Checked)

                if scroll:
                    self.scroll_to_item(item)

                self.viewport().update()
                self.update_check_state()

                return item

        return None

    def check_items(self, items: List[TreeItem]):
        for item in items:
            item.set_checked_state(Qt.CheckState.Checked)

        self.update_check_state()

    def update_check_state(self):
        self._model.check_state_changed.emit(QModelIndex())

    def batch_select(self, number_list: List[int]):
        all_items = self.get_all_items()

        for item in all_items:
            if item.number in number_list:
                item.set_checked_state(Qt.CheckState.Checked)

        self.update_check_state()

    def on_update_media_info(self, episode_data: dict):
        signal_bus.parse.preview_init.emit(episode_data, True)

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

    def _check_main_episodes_node(self):
        # 选中剧集类正片部分
        try:
            self._model.root_node.children[0].children[0].set_checked_state(Qt.CheckState.Checked)
            
        except IndexError:
            pass
    
    def on_view_cover(self, item: TreeItem):
        from ...dialog.misc.view_cover import ViewCoverDialog

        dialog = ViewCoverDialog(item.cover, parent = self.main_window)
        dialog.show()

    def update_alternate_row_color(self):
        if config.get(config.parse_list_alternate_row_color):
            self.setAlternatingRowColors(True)

            _light = """
                QTreeView {
                    background-color: transparent;
                    alternate-background-color: rgba(0, 0, 0, 0.05);
                }
            """

            _dark = """
                QTreeView {
                    background-color: transparent;
                    alternate-background-color: rgba(255, 255, 255, 0.08);
                }
            """

            setCustomStyleSheet(self, _light, _dark)
