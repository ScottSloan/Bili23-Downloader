from PySide6.QtCore import Qt, QEvent, QModelIndex, QPersistentModelIndex, QPoint, QTimer, QSize
from PySide6.QtWidgets import QApplication, QGraphicsDropShadowEffect
from PySide6.QtGui import QColor, QCursor

from qfluentwidgets import TreeView, RoundMenu, Action, CommandBarView, FluentIcon, isDarkTheme, setCustomStyleSheet

from .model import ParseModel

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

        self._hover_item = None
        self._hover_index = QPersistentModelIndex()
        self._hover_hide_timer = QTimer(self)
        self._hover_hide_timer.setSingleShot(True)
        self._hover_hide_timer.setInterval(80)
        self._hover_hide_timer.timeout.connect(self._hide_hover_bar_if_outside)

        self.setModel(self._model)
        self.setUniformRowHeights(True)
        self.setSortingEnabled(True)
        self.setSelectionMode(TreeView.SelectionMode.SingleSelection)
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)

        self._init_hover_command_bar()

        self.customContextMenuRequested.connect(self.on_context_menu)
        signal_bus.parse.update_column_settings.connect(self._setHeaderWidth)
        self._model.modelReset.connect(self._hide_hover_bar)
        config.themeChanged.connect(self._update_hover_bar_shadow)
        
        self._setHeaderWidth()
        self.update_alternate_row_color()

    def _init_hover_command_bar(self):
        self._hover_bar = CommandBarView(self.viewport())
        self._hover_bar.setToolButtonStyle(Qt.ToolButtonStyle.ToolButtonIconOnly)
        self._hover_bar.setButtonTight(True)
        self._hover_bar.setIconSize(QSize(14, 14))
        self._hover_bar.setSpaing(2)
        self._hover_bar.hBoxLayout.setContentsMargins(4, 4, 4, 4)

        self._hover_shadow = QGraphicsDropShadowEffect(self._hover_bar)
        self._hover_shadow.setBlurRadius(14)
        self._hover_shadow.setOffset(0, 2)
        self._hover_bar.setGraphicsEffect(self._hover_shadow)
        self._update_hover_bar_shadow()

        self._hover_bar.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self._hover_bar.setAttribute(Qt.WidgetAttribute.WA_ShowWithoutActivating)
        self._hover_bar.installEventFilter(self)

        self._hover_parse_action = self._create_hover_action(
            FluentIcon.SEARCH,
            self.tr("Parse this item"),
            self._on_hover_parse
        )
        self._hover_download_action = self._create_hover_action(
            FluentIcon.DOWNLOAD,
            self.tr("Download as Single Video"),
            self._on_hover_download
        )
        # 查看分P视频列表默认禁用，只有在解析收藏夹时，且对应条目为分P视频时才会启用
        self._hover_part_list_action = self._create_hover_action(
            ExtendedFluentIcon.LIST,
            self.tr("View Multi-part Video List"),
            lambda: None
        )
        self._hover_part_list_action.setEnabled(False)

        self._hover_bar.addActions([
            self._hover_parse_action,
            self._hover_part_list_action,
            self._hover_download_action,
        ])
        self._hover_bar.resizeToSuitableWidth()
        self._hover_bar.adjustSize()
        self._hover_bar.hide()

    def _update_hover_bar_shadow(self, *_):
        if not hasattr(self, "_hover_shadow"):
            return

        alpha = 100 if isDarkTheme() else 50
        self._hover_shadow.setColor(QColor(0, 0, 0, alpha))

    def _create_hover_action(self, icon, text, slot):
        action = Action(icon=icon, text=text, parent=self)
        action.setToolTip(text)
        action.triggered.connect(slot)

        return action

    def viewportEvent(self, event: QEvent):
        if config.get(config.parse_list_show_floating_command_bar):
            if event.type() == QEvent.Type.MouseMove:
                self._update_hover_bar(self.indexAt(event.position().toPoint()))

            elif event.type() == QEvent.Type.Leave:
                self._schedule_hide_hover_bar()

            elif event.type() == QEvent.Type.Resize:
                QTimer.singleShot(0, self._reposition_hover_bar)

        return super().viewportEvent(event)

    def eventFilter(self, watched, event: QEvent):
        if config.get(config.parse_list_show_floating_command_bar):
            hover_bar = getattr(self, "_hover_bar", None)

            if hover_bar is not None and watched is hover_bar:
                if event.type() == QEvent.Type.Enter:
                    self._hover_hide_timer.stop()

                elif event.type() == QEvent.Type.Leave:
                    self._schedule_hide_hover_bar()

        return super().eventFilter(watched, event)

    def _update_hover_bar(self, index: QModelIndex):
        self._hover_hide_timer.stop()

        if not index.isValid():
            self._hide_hover_bar()
            return

        item: TreeItem = index.internalPointer()

        if item is None or item.count() != 0:
            self._hide_hover_bar()
            return

        root_index = index.siblingAtColumn(0)
        if not root_index.isValid() or self._model.columnCount() == 0:
            self._hide_hover_bar()
            return

        self._hover_item = item
        self._hover_index = QPersistentModelIndex(root_index)
        self._reposition_hover_bar()

        if item.has_attribute(Attribute.FAVORITE_WITH_MULTI_PART_VIDEO_BIT):
            self._hover_part_list_action.setEnabled(True)
        else:
            self._hover_part_list_action.setEnabled(False)

    def _reposition_hover_bar(self):
        if self._hover_item is None or not self._hover_index.isValid():
            return

        last_column = self._model.columnCount() - 1

        cell_index = self._model.index(
            self._hover_index.row(),
            last_column,
            self._hover_index.parent()
        )
        cell_rect = self.visualRect(cell_index)

        if not cell_rect.isValid() or not cell_rect.intersects(self.viewport().rect()):
            self._hide_hover_bar()
            return

        bar_size = self._hover_bar.sizeHint()
        margin = 4

        if self.viewport().width() <= bar_size.width() + margin * 2:
            self._hide_hover_bar()
            return

        left = cell_rect.right() - bar_size.width() - margin
        left = max(margin, min(left, self.viewport().width() - bar_size.width() - margin))

        top = cell_rect.top() + (cell_rect.height() - bar_size.height()) // 2
        top = max(margin, min(top, self.viewport().height() - bar_size.height() - margin))

        self._hover_bar.resize(bar_size)
        self._hover_bar.move(QPoint(left, top))
        self._hover_bar.raise_()
        self._hover_bar.show()

    def _schedule_hide_hover_bar(self):
        if self._hover_bar.isVisible():
            self._hover_hide_timer.start()

    def _hide_hover_bar_if_outside(self):
        cursor_pos = QCursor.pos()
        in_viewport = self.viewport().rect().contains(self.viewport().mapFromGlobal(cursor_pos))
        in_bar = self._hover_bar.rect().contains(self._hover_bar.mapFromGlobal(cursor_pos))

        if not in_viewport and not in_bar:
            self._hide_hover_bar()

    def _hide_hover_bar(self):
        self._hover_hide_timer.stop()
        self._hover_item = None
        self._hover_index = QPersistentModelIndex()

        if hasattr(self, "_hover_bar"):
            self._hover_bar.hide()

    def _consume_hover_item(self):
        item = self._hover_item
        self._hide_hover_bar()

        return item

    def _on_hover_parse(self):
        if item := self._consume_hover_item():
            self.on_parse_item(item)

    def _on_hover_open_in_browser(self):
        if item := self._consume_hover_item():
            self.on_open_in_browser(item)

    def _on_hover_download(self):
        if item := self._consume_hover_item():
            self.on_download_as_single_video(item)

    def _on_hover_update_media_info(self):
        if item := self._consume_hover_item():
            self.on_update_media_info(item.to_dict())

    def _setHeaderWidth(self):
        self._hide_hover_bar()

        for index, entry in enumerate(config.get(config.parse_list_column)):
            self.setColumnWidth(index, entry["width"])

        # 重新展开
        self._schedule_expand_all()

        header = self.header()
        header.setStretchLastSection(False)

    def scrollContentsBy(self, dx, dy):
        super().scrollContentsBy(dx, dy)

        if self._hover_item is not None:
            self._hide_hover_bar()

    def resizeEvent(self, event):
        super().resizeEvent(event)

        if self._hover_item is not None:
            QTimer.singleShot(0, self._reposition_hover_bar)

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

        # 全局选择操作
        check_all_text = self.tr("Check All") if self._model.root_node.checked == Qt.CheckState.Unchecked else self.tr("Uncheck All")
        menu.addAction(self._create_action(ExtendedFluentIcon.SELECT_ALL, check_all_text, self.on_toggle_check_all_items))
        menu.addAction(self._create_action(ExtendedFluentIcon.RETRY, self.tr("Reverse"), self.reverse_check_state))
        menu.addSeparator()

        # 当前项操作
        check_item_text = self.tr("Check Item") if item.checked == Qt.CheckState.Unchecked else self.tr("Uncheck Item")
        menu.addAction(self._create_action(ExtendedFluentIcon.SELECT, check_item_text, lambda: self.on_toggle_check_state(item)))

        # 叶子节点操作 (无子节点的项)
        if item.count() == 0:
            menu.addAction(self._create_action(FluentIcon.SEARCH, self.tr("Parse this item"), lambda: self.on_parse_item(item)))
            menu.addAction(self._create_action(FluentIcon.GLOBE, self.tr("Open in Browser"), lambda: self.on_open_in_browser(item)))
            menu.addAction(self._create_action(FluentIcon.DOWNLOAD, self.tr("Download as Single Video"), lambda: self.on_download_as_single_video(item)))
            menu.addAction(self._create_action(ExtendedFluentIcon.RETRY, self.tr("Update Media Info"), lambda: self.on_update_media_info(item.to_dict())))

        # 元数据信息
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

    def on_parse_item(self, item: TreeItem):
        url = item.url

        signal_bus.parse.parse_url.emit(url)

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
