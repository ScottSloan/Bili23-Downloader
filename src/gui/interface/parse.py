from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QApplication
from PySide6.QtGui import QKeyEvent
from PySide6.QtCore import Qt

from qfluentwidgets import LineEdit, BodyLabel, FluentIcon, RoundMenu, Action

from gui.component.widget import TransparentToolButton, SegmentedWidget, IndeterminateProgressPushButton
from gui.dialog.download_options.dialog import DownloadOptionsDialog
from gui.dialog.misc import SearchDialog, BatchSelectDialog
from gui.component.parse.tree_view import ParseTreeView

from util.common import signal_bus, config, Translator, ExtendedFluentIcon
from util.common.enum import ToastNotificationCategory, NumberingType
from util.parse.preview import Previewer, PreviewerInfo
from util.common.data import url_patterns
from util.parse.worker import ParseWorker
from util.thread import AsyncTask

from functools import wraps
import re

def check_preview_info(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if PreviewerInfo.error_occurred:
            # 只有存在 error_message 时才显示通知

            if PreviewerInfo.error_message:
                signal_bus.toast.show.emit(ToastNotificationCategory.ERROR, Translator.ERROR_MESSAGES("MEDIA_INFO_FAILED"), PreviewerInfo.error_message)
        else:
            return func(self, *args, **kwargs)
        
    return wrapper

def show_download_options_dialog(func):
    @wraps(func)
    def wrapper(self, *args, **kwargs):
        if config.get(config.show_download_options_dialog):
            dialog = DownloadOptionsDialog(self.main_window)
            
            if not dialog.exec():
                return

        return func(self, *args, **kwargs)
    
    return wrapper

class ParseBase(QFrame):
    def __init__(self, parent = None):
        super().__init__(parent = parent)

        self.category_name = ""

    def check_pager_visibility(self, extra_data: dict):
        # 根据解析结果判断是否显示分页组件
        if extra_data:
            if extra_data.get("pagination"):
                self.segmented_widget.show_pager(extra_data["pagination_data"])
        else:
            self.segmented_widget.hide_pager()

    def check_need_check_all(self):
        # 如果解析结果只有一个视频，或者配置了自动全选，则直接勾选所有项目
        if self.parse_list.get_total_items_count() == 1 or config.get(config.auto_check_all):
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

    def scroll_to_item(self, tree_item):
        self.parse_list.scroll_to_item(tree_item)

    def check_matches(self, items):
        self.parse_list.check_items(items)

class ParseInterface(ParseBase):
    def __init__(self, parent = None):
        super().__init__(parent = parent)

        self.main_window = parent

        self.setObjectName("ParseInterface")

        self.init_UI()

        self.init_utils()

    def init_UI(self):
        self.url_box = LineEdit(self)
        self.url_box.setPlaceholderText(self.tr("Link / av / BV / ep / ss / md / Favorites / Profile"))

        self.url_box.setClearButtonEnabled(True)

        self.parse_btn = IndeterminateProgressPushButton(self.tr("Parse"), self)
        self.parse_btn.setMinimumWidth(80)

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

        self.download_btn = IndeterminateProgressPushButton(self.tr("Download Selected Items"), self)
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
        self.parse_btn.clicked.connect(lambda _: self.on_parse())
        self.segmented_widget.pager_widget.pageChanged.connect(self.on_parse)
        self.url_box.returnPressed.connect(self.on_parse)

        self.download_option_btn.clicked.connect(self.on_download_options)
        self.show_more_btn.clicked.connect(self.on_show_more)

        self.parse_list._model.check_state_changed.connect(self.on_item_check_state_changed)
        self.download_btn.clicked.connect(self.on_download)

        signal_bus.parse.update_parse_list.connect(self.parse_list.update_tree)

        self.segmented_widget.search_widget.scrollToItem.connect(self.scroll_to_item)
        self.segmented_widget.search_widget.checkMatches.connect(self.check_matches)

    def init_utils(self):
        self.previewer = Previewer()

        self.clipboard = QApplication.clipboard()
        self.clipboard.changed.connect(self.on_copy_url)

    def on_parse(self, page: int = 1):
        self.reset_search()
        self.parse_btn.setIndeterminateState(True)

        worker = ParseWorker(self.url_box.text(), page)
        worker.success.connect(self.on_parse_success)
        worker.error.connect(self.on_parse_error)
        
        AsyncTask.run(worker)

    def on_parse_success(self, category_name: str, extra_data: dict):
        if first_episode_info := self.parse_list.get_first_item_info():
            self.category_name = Translator.EPISODE_TYPE(category_name)

            # 获取解析结果中第一个视频的信息，作为预览的媒体信息
            signal_bus.parse.preview_init.emit(first_episode_info)

        self.on_item_check_state_changed(None)

        # 根据解析结果判断是否显示分页组件
        self.check_pager_visibility(extra_data)

        self.check_need_check_all()

        self.parse_btn.setIndeterminateState(False)

    def on_parse_error(self, error_message: str):
        self.parse_btn.setIndeterminateState(False)

        signal_bus.toast.show.emit(ToastNotificationCategory.ERROR, self.tr("Parse Failed"), error_message)

    @check_preview_info
    @show_download_options_dialog
    def on_download(self):
        # 只有在获取媒体信息成功时才允许下载
        #self.download_btn.setIndeterminateState(True)

        checked_episodes_list = self.parse_list.get_checked_items(to_dict = True)

        self.check_starting_number()

        signal_bus.download.create_task.emit(checked_episodes_list)

        signal_bus.toast.show.emit(ToastNotificationCategory.SUCCESS, "", self.tr("Added to download queue"))

    @check_preview_info
    def on_download_options(self):
        # 只有在获取媒体信息成功时才显示下载选项对话框
        dialog = DownloadOptionsDialog(self.main_window)
        dialog.exec()

    def on_show_more(self):
        menu = RoundMenu(parent = self)

        # TODO: 筛选功能
        search_action = Action(icon = FluentIcon.SEARCH, text = self.tr("Search"), parent = self)
        search_action.triggered.connect(self.on_search)
        # filter_action = Action(icon = FluentIcon.FILTER, text = self.tr("筛选"), parent = self)
        batch_select_action = Action(icon = ExtendedFluentIcon.TODO, text = self.tr("Select multiple"), parent = self)
        batch_select_action.triggered.connect(self.on_batch_select)

        menu.addAction(search_action)
        # menu.addAction(filter_action)
        menu.addAction(batch_select_action)

        pos = self.show_more_btn.mapToGlobal(self.show_more_btn.rect().bottomLeft())

        menu.exec(pos)

    def on_search(self):
        dialog = SearchDialog(self.main_window)
        
        if dialog.exec():
            matches = self.parse_list.search_keywords(dialog.keywords)

            self.segmented_widget.show_search(matches)

    def on_batch_select(self):
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
        if self.clipboard.mimeData().hasText() and config.get(config.listen_clipboard):
            url = self.clipboard.text()

            for parser_type, pattern in url_patterns:
                if re.findall(pattern, url):
                    self.url_box.setText(url)
                    self.on_parse()

                    return parser_type

    def keyPressEvent(self, event: QKeyEvent):
        if event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_A:
            self.parse_list.check_all_items()

            event.accept()

        elif event.modifiers() == Qt.KeyboardModifier.ControlModifier and event.key() == Qt.Key.Key_D:
            self.parse_list.check_all_items(uncheck = True)

            event.accept()
            
        else:
            return super().keyPressEvent(event)
