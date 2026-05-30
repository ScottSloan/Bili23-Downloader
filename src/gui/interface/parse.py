from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QApplication
from PySide6.QtCore import Qt, QTimer
from PySide6.QtGui import QKeyEvent

from qfluentwidgets import (
    LineEdit, BodyLabel, FluentIcon, RoundMenu, Action, PrimaryPushButton, InfoBarIcon,
    TeachingTipTailPosition, TeachingTip
)

from gui.component.widget import (
    TransparentToolButton, SegmentedWidget, IndeterminateProgressPushButton, SeasonComboBox, ProgressTipWidget,
)
from gui.component.parse_list import ParseTreeView

from util.common.enum import ToastNotificationCategory, NumberingType
from util.common.signal_bus import signal_bus, config
from util.common.icon import ExtendedFluentIcon
from util.common.translator import Translator
from util.common.data import url_patterns
from util.common.config import config

from util.parse.worker import ParseWorker, ProgressParseWorker
from util.parse.preview.previewer import Previewer
from util.parse.preview.info import PreviewerInfo

from util.misc.history import history_manager
from util.download.task.manager import task_manager
from util.thread.pool import GlobalThreadPoolTask
from util.thread.async_ import AsyncTask

import re

class ParseBase(QFrame):
    def __init__(self, parent = None):
        super().__init__(parent = parent)

        self.category_name = ""

    def check_extra_data(self, extra_data: dict):
        if extra_data:
            # 判断是否显示分页组件
            if extra_data.get("pagination"):
                self.segmented_widget.show_pager(extra_data["pagination_data"])

                # 具有分页信息，且总页数大于 1 时，根据设置弹出自动解析分页对话框
                if extra_data["pagination_data"]["total_pages"] > 1:
                    if not config.get(config.auto_parse_teaching_tip_shown):
                        # 仅提示一次
                        config.set(config.auto_parse_teaching_tip_shown, True)

                        QTimer.singleShot(0, self.show_auto_parse_teaching_tip)

                    if config.get(config.show_auto_parse_dialog):
                        QTimer.singleShot(0, self.on_auto_parse)
                    
            else:
                self.segmented_widget.hide_pager()

            # 判断是否显示季选择组件
            if extra_data.get("seasons"):
                self.season_choice.update_data(extra_data["season_data"])
            else:
                self.season_choice.hide()
        else:
            self.segmented_widget.hide_pager()

            self.season_choice.hide()

    def check_need_check_all(self):
        # 如果配置了自动全选，则直接勾选所有项目
        if config.get(config.auto_check_all):
            self.parse_list.check_all_items()

            self.download_btn.setEnabled(True)

    def check_starting_number(self):
        # 更新当前起始编号，如果尚未设置
        if config.current_starting_number is None:
            if config.get(config.numbering_type) == NumberingType.CONTINUOUS:
                config.current_starting_number = config.global_starting_number
            else:
                config.current_starting_number = config.get(config.starting_number)

    def reset_search(self):
        self.parse_list.search_keywords(None)

        self.segmented_widget.hide_search()

    def reset_parse_list(self):
        PreviewerInfo.error_occurred = True

        self.parse_list.clear_tree()

        self.item_count_label.setText("")

    def scroll_to_item(self, tree_item):
        self.parse_list.scroll_to_item(tree_item)

    def check_matches(self, items):
        self.parse_list.check_items(items)

    def update_previewer_info(self):
        if first_episode_info := self.parse_list.get_first_item_info():
            # 获取解析结果中第一个视频的信息，作为预览的媒体信息
            signal_bus.parse.preview_init.emit(first_episode_info)

    def check_preview_info(self):
        if PreviewerInfo.error_occurred:
            # 只有存在 error_message 时才显示通知

            if PreviewerInfo.error_message:
                signal_bus.toast.show.emit(ToastNotificationCategory.ERROR, Translator.ERROR_MESSAGES("MEDIA_INFO_FAILED"), PreviewerInfo.error_message)

            return False
        else:
            return True

    def adjust_column_width(self):
        header = self.parse_list.header()

        header.setSectionResizeMode(1, header.ResizeMode.Stretch)

    def reparse(self, url: str):
        self.url_box.setText(url)
        
        self.on_parse()

    def on_show_interactive_video_dialog(self, data: dict):
        # 显示互动视频对话框，询问用户是否探查所有节点
        from gui.dialog.misc.interactive_video import InteractiveVideoDialog

        dialog = InteractiveVideoDialog(data, self.main_window)

        if dialog.exec():
            self.start_progress_parse_worker(dialog.payload)

    def start_progress_parse_worker(self, data: dict):
        # 启动专门用于解析互动视频的后台线程，并连接进度更新信号
        worker = ProgressParseWorker(data)
        worker.success.connect(self.on_parse_success)
        worker.error.connect(self.on_parse_error)
        worker.finished.connect(self.on_progress_parse_finished)
        worker.update_progress.connect(self.on_progress_update)

        self.progress_widget._trigger_stop_callback = worker.trigger_stop
        self.progress_widget.show_tip()

        AsyncTask.run(worker)

    def on_progress_parse_finished(self):
        self.progress_widget.hide_tip()

    def on_progress_update(self, message: str):
        self.progress_widget.update_text(message)

    def on_update_parse_list_count(self, category_name: str, count: int):
        # 更新解析结果总数的显示
        self.category_name = Translator.EPISODE_TYPE(category_name)

        text_label = self.tr("{category_name} ({total_count} total)").format(
            category_name = self.category_name,
            total_count = count
        )

        self.item_count_label.setText(text_label)

    def on_auto_parse(self):
        from gui.dialog.misc.auto_parse import AutoParseDialog

        dialog = AutoParseDialog(self.url_box.text(), self.pager.total_pages, self.pager.current_page, self.main_window)

        if dialog.exec():
            # 开始解析前，隐藏分页组件
            self.segmented_widget.hide_pager()
            
            self.start_progress_parse_worker(dialog.payload)

    def show_auto_parse_teaching_tip(self):
        TeachingTip.create(
            target = self.segmented_widget.pager_widget.menu_btn,
            title = self.tr("Auto-parse Pagination"),
            content = self.tr("Click here to automatically parse all pages."),
            icon = InfoBarIcon.INFORMATION,
            tailPosition = TeachingTipTailPosition.BOTTOM,
            isClosable = True,
            duration = -1,
            parent = self.main_window
        )

    def post_parse_success_check(self, extra_data: dict):
        # 根据解析结果判断是否显示分页组件
        self.check_extra_data(extra_data)

        self.check_need_check_all()

        if config.get(config.show_download_confirmation_dialog) and self._triggered_by_clipboard:
            # 重置标志位
            self._triggered_by_clipboard = False

            # 显示下载确认对话框
            QTimer.singleShot(1000, self.on_download)

    def show_download_options_dialog(self):
        from ..dialog.download_options.dialog import DownloadOptionsDialog

        dialog = DownloadOptionsDialog(self.main_window)
        
        return dialog
    
class ParseInterface(ParseBase):
    def __init__(self, parent = None):
        super().__init__(parent = parent)

        self.main_window = parent
        self._triggered_by_clipboard = False
        self.download_options_dialog_opened = False

        self.setObjectName("ParseInterface")

        self.init_UI()

        self.init_utils()

    def init_UI(self):
        paste_action = Action(icon = FluentIcon.PASTE, text = self.tr("Paste and Parse"), parent = self)
        paste_action.triggered.connect(lambda _: self.on_paste_and_parse())

        self.url_box = LineEdit(self)
        self.url_box.setPlaceholderText(self.tr("Link / av / BV / ep / ss / md / Favorites / Profile"))
        self.url_box.addAction(paste_action, LineEdit.ActionPosition.TrailingPosition)

        self.url_box.setClearButtonEnabled(True)

        self.parse_btn = IndeterminateProgressPushButton(self.tr("Parse"), self)
        self.parse_btn.setMinimumWidth(80)

        # dropdown_menu = RoundMenu(parent = self.parse_btn)
        # dropdown_menu.addAction(self._create_action(ExtendedFluentIcon.AUTOMATION, self.tr("自动解析分页"), self.on_auto_parse))

        # self.parse_btn.setFlyout(dropdown_menu)

        self.item_count_label = BodyLabel("", self)

        self.download_option_btn = TransparentToolButton(ExtendedFluentIcon.OPTIONS, self)
        self.download_option_btn.setToolTip(self.tr("Download Options"))
        self.download_option_btn.setFixedSize(28, 28)

        self.show_more_btn = TransparentToolButton(FluentIcon.MORE, self)
        self.show_more_btn.setToolTip(self.tr("More"))
        self.show_more_btn.setFixedSize(28, 28)

        self.parse_list = ParseTreeView(self.main_window, parent = self)

        self.segmented_widget = SegmentedWidget(self)
        self.segmented_widget.hide()

        self.season_choice = SeasonComboBox(self)
        self.season_choice.setFixedWidth(150)
        self.season_choice.hide()

        self.progress_widget = ProgressTipWidget(self)
        self.progress_widget.hide()

        self.download_btn = PrimaryPushButton(text = self.tr("Download Selected Items"), parent = self)
        self.download_btn.setMinimumWidth(120)
        self.download_btn.setEnabled(False)

        top_layout = QHBoxLayout()
        top_layout.addWidget(self.url_box)
        top_layout.addWidget(self.parse_btn)

        toolbar_layout = QHBoxLayout()
        toolbar_layout.addWidget(self.item_count_label)
        toolbar_layout.addStretch()
        toolbar_layout.addWidget(self.download_option_btn)
        toolbar_layout.addWidget(self.show_more_btn)

        bottom_layout = QHBoxLayout()
        bottom_layout.addWidget(self.segmented_widget)
        bottom_layout.addWidget(self.season_choice)
        bottom_layout.addWidget(self.progress_widget)
        bottom_layout.addStretch()
        bottom_layout.addWidget(self.download_btn)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 15, 25, 15)
        main_layout.addLayout(top_layout)
        main_layout.addLayout(toolbar_layout)
        main_layout.addWidget(self.parse_list)
        main_layout.addSpacing(10)
        main_layout.addLayout(bottom_layout)

        self.connect_signals()

    def connect_signals(self):
        self.parse_btn.clicked.connect(lambda: self.on_parse())
        self.segmented_widget.pager_widget.pageChanged.connect(lambda page: self.on_parse(page))
        self.url_box.returnPressed.connect(lambda: self.on_parse())

        self.download_option_btn.clicked.connect(self.on_download_options)
        self.show_more_btn.clicked.connect(self.on_top_layout_show_more_menu)

        self.parse_list._model.check_state_changed.connect(self.on_item_check_state_changed)
        self.download_btn.clicked.connect(self.on_download)

        signal_bus.parse.update_parse_list.connect(self.on_update_parse_list)
        signal_bus.parse.update_parse_list_count.connect(self.on_update_parse_list_count)
        signal_bus.parse.update_preview_info.connect(self.update_previewer_info)
        signal_bus.parse.search_keyword.connect(self.parse_list.search_keywords)
        signal_bus.parse.show_interactive_video_dialog.connect(self.on_show_interactive_video_dialog)

        self.segmented_widget.search_widget.scrollToItem.connect(self.scroll_to_item)
        self.segmented_widget.search_widget.checkMatches.connect(self.check_matches)
        self.segmented_widget.pager_widget.menu_btn.clicked.connect(self.on_pager_show_more_menu)

        self.season_choice.changeSeason.connect(self.on_season_changed)

    def init_utils(self):
        self.previewer = Previewer()

        self.clipboard = QApplication.clipboard()
        self.clipboard.changed.connect(self.on_copy_url)

        self.check_starting_number()

    def on_paste_and_parse(self):
        url = self.clipboard.text()

        if not url:
            return

        self.url_box.setText(url)

        self.on_parse()

    def on_parse(self, page: int = 1):
        self.parse_btn.setIndeterminateState(True)

        worker = ParseWorker(self.url_box.text(), page)
        worker.success.connect(self.on_parse_success)
        worker.error.connect(self.on_parse_error)

        AsyncTask.run(worker)

    def on_parse_success(self, category_name: str, extra_data: dict):
        self.parse_list._model._set_category_name(category_name)
        self.category_name = Translator.EPISODE_TYPE(category_name)

        self.update_previewer_info()

        self.post_parse_success_check(extra_data)

        self.on_item_check_state_changed(None)
        self.parse_btn.setIndeterminateState(False)
        # 清空搜索关键词
        self.parse_list.search_keywords("")

    def on_parse_error(self, error_message: str):
        self.parse_btn.setIndeterminateState(False)
        self.progress_widget.hide_tip()

        # 重置解析结果和搜索状态
        self.reset_search()
        self.reset_parse_list()

        signal_bus.toast.show.emit(ToastNotificationCategory.ERROR, self.tr("Parse Failed"), error_message)

    def on_update_parse_list(self, title: str, category_name: str, root_node, current_episode_data: dict):
        self.parse_list.update_tree(root_node, current_episode_data)

        if config.get(config.parse_history):
            history_manager.add_history(title, self.url_box.text(), category_name)

    def on_download(self):
        # 只有在获取媒体信息成功时才允许下载
        #self.download_btn.setIndeterminateState(True)

        if not self.check_preview_info():
            return

        if config.get(config.show_download_options_dialog):
            dialog = self.show_download_options_dialog()

            if not dialog.exec():
                return
            
        checked_episodes_list = self.parse_list.get_checked_items(to_dict = True, mark_as_downloaded = True)

        GlobalThreadPoolTask.run_func(task_manager.create, checked_episodes_list)

        signal_bus.toast.show.emit(ToastNotificationCategory.SUCCESS, "", self.tr("Added to download queue"))

        QTimer.singleShot(0, self.parse_list.update_check_state)

    def on_download_options(self):
        # 只有在获取媒体信息成功时才显示下载选项对话框
        if not self.check_preview_info():
            return
        
        dialog = self.show_download_options_dialog()
        dialog.exec()

    def on_top_layout_show_more_menu(self):
        menu = RoundMenu(parent = self)

        menu.addAction(self._create_action(FluentIcon.SEARCH, self.tr("Search"), self.on_search))
        menu.addAction(self._create_action(ExtendedFluentIcon.TODO, self.tr("Batch select"), self.on_batch_select))
        menu.addAction(self._create_action(FluentIcon.HISTORY, self.tr("Parsing history"), self.on_history))

        pos = self.show_more_btn.mapToGlobal(self.show_more_btn.rect().bottomLeft())

        menu.exec(pos)

    def on_pager_show_more_menu(self, page):
        menu = RoundMenu(parent = self)

        menu.addAction(self._create_action(FluentIcon.DOCUMENT, self.tr("Jump to page"), self.on_jump_to_page))
        menu.addAction(self._create_action(ExtendedFluentIcon.AUTOMATION, self.tr("Auto-parse pagination"), self.on_auto_parse))

        pos = self.pager.menu_btn.mapToGlobal(self.pager.menu_btn.rect().bottomLeft())

        menu.exec(pos)

    def on_search(self):
        from ..dialog.misc.search import SearchDialog

        dialog = SearchDialog(self.main_window)
        
        if dialog.exec():
            matches = self.parse_list.search_keywords(dialog.keywords)

            self.segmented_widget.show_search(matches)

    def on_batch_select(self):
        from ..dialog.misc.batch_select import BatchSelectDialog

        dialog = BatchSelectDialog(self.main_window)

        if dialog.exec():
            self.parse_list.batch_select(dialog.number_list)

    def on_item_check_state_changed(self, index):
        checked_count = self.parse_list.get_checked_items_count()
        total_count = self.parse_list.get_total_items_count()

        if checked_count:
            text_label = self.tr("{category_name} ({selected_count} selected, {total_count} total)").format(
                category_name = self.category_name,
                selected_count = checked_count,
                total_count = total_count
            )
        else:
            text_label = self.tr("{category_name} ({total_count} total)").format(
                category_name = self.category_name,
                total_count = total_count
            )

        self.item_count_label.setText(text_label)
        self.download_btn.setEnabled(checked_count > 0)

    def on_copy_url(self):
        # 只有当剪贴板内容为文本且符合 URL 模式，并且用户启用了监控剪贴板功能，且当前没有打开下载选项对话框时，才自动解析剪贴板中的链接
        if self.clipboard.mimeData().hasText() and config.get(config.monitor_clipboard) and not self.download_options_dialog_opened:
            url = self.clipboard.text()

            for parser_type, pattern in url_patterns:
                if re.findall(pattern, url):
                    # 置标志位，表示接下来的解析是由监控剪贴板触发的
                    self._triggered_by_clipboard = True

                    self.url_box.setText(url)
                    self.on_parse()

                    return parser_type

    def on_history(self):
        from ..dialog.misc.parse_history import ParseHistoryDialog

        dialog = ParseHistoryDialog(self.main_window)
        dialog.exec()

    def on_jump_to_page(self):
        from ..dialog.misc.jump_to_page import JumpToPageDialog

        dialog = JumpToPageDialog(self.main_window)

        if dialog.exec():
            page_number = dialog.page

            if 1 <= page_number <= self.pager.total_pages:
                self.segmented_widget.pager_widget.on_change_page(page_number)

            else:
                signal_bus.toast.show.emit(ToastNotificationCategory.WARNING, self.tr("Invalid page number"), self.tr("Please enter a number between 1 and {total_pages}").format(total_pages = self.pager.total_pages))

    def keyPressEvent(self, event: QKeyEvent):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_A:
            # Ctrl + A 快捷键全选
            self.parse_list.check_all_items()

            event.accept()

            return

        elif event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_D:
            # Ctrl + D 快捷键全不选
            self.parse_list.check_all_items(uncheck = True)

            event.accept()

            return
        
        elif event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_F:
            # Ctrl + F 快捷键打开搜索对话框
            self.on_search()

            event.accept()

            return
            
        else:
            return super().keyPressEvent(event)

    def _create_action(self, icon, text, slot):
        action = Action(icon = icon, text = text, parent = self)
        action.triggered.connect(slot)

        return action
    
    def on_season_changed(self, url: str):
        # 切换季时重新解析
        self.reparse(url)

    @property
    def pager(self):
        return self.segmented_widget.pager_widget