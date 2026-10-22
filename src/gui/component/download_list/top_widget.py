from PySide6.QtWidgets import QStackedWidget, QWidget, QHBoxLayout, QGridLayout, QButtonGroup, QSizePolicy
from PySide6.QtCore import Qt, QEvent, Signal

from qfluentwidgets import (
    PrimaryPushButton, PushButton, FluentIcon, FlyoutViewBase, BodyLabel, ComboBox, FlyoutAnimationType,
    CheckBox, SearchLineEdit
)

from gui.component.widget.button import ToolButton, ToggleToolButton
from gui.component.widget.flyout_popup import Flyout
from gui.component.widget.separator import Separator

from util.common.enum import DownloadStatus
from util.common.icon import ExtendedFluentIcon
from util.common.translator import Translator
from util.common.io.directory import Directory
from util.common.signal_bus import signal_bus
from util.common.config import config

def get_media_type_group_dict():
    """
    筛选浮窗的类型选项：label → 一组 get_media_type_key 的取值

    选项文案直接用封面角标那一组，与列表里看到的角标逐字对得上。互动视频不单列：
    它同时带着 VIDEO_BIT，重新解析、命名规则等处都按投稿视频对待，勾「视频」却筛不出
    互动视频反而奇怪。封面角标仍标「互动」，那里是展示细分类型，不涉及归类
    """
    return {
        Translator.MEDIA_TYPE_BADGE("VIDEO"): frozenset({"VIDEO", "INTERACTIVE"}),
        Translator.MEDIA_TYPE_BADGE("BANGUMI"): frozenset({"BANGUMI"}),
        Translator.MEDIA_TYPE_BADGE("COURSE"): frozenset({"COURSE"}),
        Translator.MEDIA_TYPE_BADGE("AUDIO"): frozenset({"AUDIO"})
    }

class SortFlyoutWidget(FlyoutViewBase):
    closed = Signal()

    def __init__(
        self, parent = None, sort_by_key_dict: dict = None,
        trigger_signal_func = None, sort_by_key = None, ascending = True
    ):
        super().__init__(parent)

        self.sort_by_key_dict = sort_by_key_dict
        self.trigger_signal_func = trigger_signal_func
        self.sort_by_key = sort_by_key
        self.ascending = ascending

        self.init_UI()

    def init_UI(self):
        sort_by_lab = BodyLabel(self.tr("Sort By"), self)

        self.sort_by_choice = ComboBox(self)
        
        for label, key in self.sort_by_key_dict.items():
            self.sort_by_choice.addItem(label, userData = key)

            if key == self.sort_by_key:
                self.sort_by_choice.setCurrentIndex(self.sort_by_choice.count() - 1)

        sort_direction_lab = BodyLabel(self.tr("Sort Direction"), self)
        self.sort_ascending_btn = ToolButton(ExtendedFluentIcon.SORT, self)
        self.sort_ascending_btn.setToolTip(self.tr("Ascending"))
        self.sort_descending_btn = ToolButton(ExtendedFluentIcon.SORT_REVERSE, self)
        self.sort_descending_btn.setToolTip(self.tr("Descending"))

        self.sort_direction_group = QButtonGroup(self)
        self.sort_direction_group.setExclusive(True)
        self.sort_direction_group.addButton(self.sort_ascending_btn)
        self.sort_direction_group.addButton(self.sort_descending_btn)

        self.sort_ascending_btn.setCheckable(True)
        self.sort_descending_btn.setCheckable(True)
        self.sort_ascending_btn.setChecked(self.ascending)
        self.sort_descending_btn.setChecked(not self.ascending)

        sort_direction_layout = QHBoxLayout()
        sort_direction_layout.setContentsMargins(0, 0, 0, 0)
        sort_direction_layout.addWidget(self.sort_ascending_btn)
        sort_direction_layout.addWidget(self.sort_descending_btn)
        sort_direction_layout.addStretch()

        main_layout = QGridLayout(self)
        main_layout.setContentsMargins(18, 12, 18, 12)
        main_layout.addWidget(sort_by_lab, 0, 0)
        main_layout.addWidget(self.sort_by_choice, 0, 2)
        main_layout.addWidget(sort_direction_lab, 1, 0)
        main_layout.addLayout(sort_direction_layout, 1, 2)

        main_layout.setColumnMinimumWidth(1, 12)

        self.connect_signals()

    def connect_signals(self):
        self.sort_by_choice.currentIndexChanged.connect(self.on_sort_by_changed)
        self.sort_ascending_btn.clicked.connect(self.on_sort_ascending)
        self.sort_descending_btn.clicked.connect(self.on_sort_descending)

    def on_sort_by_changed(self, index):
        self.sort_by_key = self.sort_by_choice.itemData(index)

        self.trigger_signal()

    def on_sort_ascending(self):
        self.ascending = True

        self.trigger_signal()

    def on_sort_descending(self):
        self.ascending = False

        self.trigger_signal()

    def trigger_signal(self):
        if self.trigger_signal_func:
            self.trigger_signal_func(self.sort_by_key, self.ascending)

        self.closed.emit()

class FilterFlyoutWidget(FlyoutViewBase):
    """
    列表的状态 / 类型筛选

    同一组内一项都不勾等于不按这一组筛选，勾了哪几项就只显示哪几项。
    与排序浮窗不同，勾选后不关闭：多选要连着点好几下，每点一下就关掉反而难用
    """
    changed = Signal()

    def __init__(
        self, parent = None, status_group_dict: dict = None, media_type_dict: dict = None,
        trigger_signal_func = None, status_filter = frozenset(), media_type_filter = frozenset()
    ):
        super().__init__(parent)

        # 两栏都按组给出：label → 一组 DownloadStatus / 一组媒体类型 key，勾一项等于纳入这一整组。
        # 已完成列表里只有一种状态，状态传 None 不显示这一栏
        self.status_group_dict = status_group_dict or {}
        self.media_type_dict = media_type_dict or {}
        self.trigger_signal_func = trigger_signal_func

        self.status_check_box_list: list[tuple[CheckBox, frozenset]] = []
        self.media_type_check_box_list: list[tuple[CheckBox, frozenset]] = []

        self.init_UI(status_filter, media_type_filter)

    def init_UI(self, status_filter: frozenset, media_type_filter: frozenset):
        main_layout = QGridLayout(self)
        main_layout.setContentsMargins(18, 12, 18, 12)
        main_layout.setColumnMinimumWidth(1, 12)
        main_layout.setVerticalSpacing(10)

        row = 0

        if self.status_group_dict:
            status_lab = BodyLabel(self.tr("Status"), self)

            self.status_check_box_list = self._create_check_box_list(self.status_group_dict, status_filter)

            main_layout.addWidget(status_lab, row, 0)
            main_layout.addLayout(self._create_check_box_layout(self.status_check_box_list), row, 2)

            row += 1

        media_type_lab = BodyLabel(self.tr("Type"), self)

        self.media_type_check_box_list = self._create_check_box_list(self.media_type_dict, media_type_filter)

        main_layout.addWidget(media_type_lab, row, 0)
        main_layout.addLayout(self._create_check_box_layout(self.media_type_check_box_list), row, 2)

        self.reset_btn = PushButton(self.tr("Reset"), self)

        reset_layout = QHBoxLayout()
        reset_layout.setContentsMargins(0, 0, 0, 0)
        reset_layout.addStretch()
        reset_layout.addWidget(self.reset_btn)

        main_layout.addLayout(reset_layout, row + 1, 0, 1, 3)

        self.connect_signals()

    def _create_check_box_list(self, group_dict: dict, current_filter: frozenset):
        check_box_list = []

        for label, group in group_dict.items():
            check_box = CheckBox(self._escape_mnemonic(label), self)
            # 筛选条件是按组内成员存的，一组成员全在条件里才算这一项被勾选
            check_box.setChecked(bool(current_filter) and group <= current_filter)

            check_box_list.append((check_box, group))

        return check_box_list

    def _escape_mnemonic(self, text: str):
        # 按钮文字里的 & 会被当成助记符吞掉，「Film & TV」会显示成「Film  TV」
        return text.replace("&", "&&")

    def _create_check_box_layout(self, check_box_list: list):
        layout = QGridLayout()
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setHorizontalSpacing(16)
        layout.setVerticalSpacing(5)

        for index, (check_box, _) in enumerate(check_box_list):
            layout.addWidget(check_box, index // 3, index % 3)

        return layout

    def connect_signals(self):
        for check_box, _ in self.status_check_box_list + self.media_type_check_box_list:
            check_box.stateChanged.connect(self.trigger_signal)

        self.reset_btn.clicked.connect(self.on_reset)

    def on_reset(self):
        # 逐个取消勾选会触发一串 stateChanged，每次都重新过滤一遍，这里屏蔽后统一触发一次
        for check_box, _ in self.status_check_box_list + self.media_type_check_box_list:
            check_box.blockSignals(True)
            check_box.setChecked(False)
            check_box.blockSignals(False)

        self.trigger_signal()

    def trigger_signal(self):
        statuses = self._collect_checked(self.status_check_box_list)
        media_types = self._collect_checked(self.media_type_check_box_list)

        if self.trigger_signal_func:
            self.trigger_signal_func(statuses, media_types)

        self.changed.emit()

    def _collect_checked(self, check_box_list: list):
        checked = set()

        for check_box, group in check_box_list:
            if check_box.isChecked():
                checked |= group

        return checked

class ExpandableSearchBox(QWidget):
    """
    顶栏的搜索框：空间宽裕时直接显示，不够时收成一个按钮，点击后再展开

    默认窗口宽度下「正在下载」页的按钮已经接近排满，再常驻一个搜索框，顶栏会被塞得满满当当。
    有搜索词时始终保持展开：筛选在生效却只剩一个图标，用户会以为任务丢了
    """
    textChanged = Signal(str)

    FULL_WIDTH = 200
    MIN_WIDTH = 120
    # 常驻显示不光要放得下搜索框，左侧还得留出这么多空白，否则顶栏看着仍是满的
    SPARE_WIDTH = 60

    def __init__(self, parent = None):
        super().__init__(parent)

        self._pinned = True
        self._expanded = False
        self._available_width = self.FULL_WIDTH + self.SPARE_WIDTH

        self.search_btn = ToolButton(FluentIcon.SEARCH, self)

        self.line_edit = SearchLineEdit(self)
        self.line_edit.installEventFilter(self)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        layout.addWidget(self.search_btn)
        layout.addWidget(self.line_edit)

        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Fixed)

        self.search_btn.clicked.connect(self.expand)
        self.line_edit.textChanged.connect(self.textChanged)

        self._update_state()

    def setPlaceholderText(self, text: str):
        self.line_edit.setPlaceholderText(text)
        self.search_btn.setToolTip(text)

    def text(self):
        return self.line_edit.text()

    def isCollapsed(self):
        # 用 isHidden 而不是 isVisible：后者在所在页面没显示时恒为 False
        return self.line_edit.isHidden()

    def setAvailableWidth(self, width: int):
        self._available_width = width
        self._pinned = width >= self.FULL_WIDTH + self.SPARE_WIDTH

        self._update_state()

    def expand(self):
        self._expanded = True

        self._update_state()

        self.line_edit.setFocus()

    def collapse(self):
        self._expanded = False

        self._update_state()

    def _update_state(self):
        show_line_edit = self._pinned or self._expanded or bool(self.line_edit.text())

        if show_line_edit:
            if self._pinned:
                width = self.FULL_WIDTH
            else:
                # 临时展开时有多少空间用多少，但不小于 MIN_WIDTH，太窄连一个词都看不全
                width = max(self.MIN_WIDTH, min(self.FULL_WIDTH, self._available_width))

            self.line_edit.setFixedWidth(width)

        self.search_btn.setVisible(not show_line_edit)
        self.line_edit.setVisible(show_line_edit)

    def eventFilter(self, obj, e: QEvent):
        if obj is self.line_edit:
            match e.type():
                case QEvent.Type.FocusOut:
                    # 弹出右键菜单也会让输入框失焦，此时不能收起
                    if e.reason() != Qt.FocusReason.PopupFocusReason and not self.line_edit.text():
                        self.collapse()

                case QEvent.Type.KeyPress if e.key() == Qt.Key.Key_Escape:
                    self.line_edit.clear()
                    self.collapse()

                    return True

        return super().eventFilter(obj, e)

class TopStackedWidget(QStackedWidget):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.download_interface = parent

        self.setFixedHeight(32)

        self.init_UI()

    def init_UI(self):
        downloading_widget = QWidget()
        downloading_widget.setContentsMargins(0, 0, 0, 0)

        self.search_downloading_list_box = self._create_search_box()

        self.filter_downloading_list_btn = ToolButton(FluentIcon.FILTER, self)
        self.filter_downloading_list_btn.setToolTip(self.tr("Filter"))

        self.sort_downloading_list_btn = ToolButton(ExtendedFluentIcon.SORT, self)
        self.sort_downloading_list_btn.setToolTip(self.tr("Sort"))

        self.open_folder_1_btn = ToolButton(FluentIcon.FOLDER, self)
        self.open_folder_1_btn.setToolTip(self.tr("Open Download Directory"))

        separator_1 = Separator(self, alpha = 50)

        self.start_all_btn = PrimaryPushButton(FluentIcon.PLAY, self.tr("Start All"), self)
        self.pause_all_btn = PushButton(FluentIcon.PAUSE, self.tr("Pause All"), self)
        self.delete_all_btn = PushButton(FluentIcon.DELETE, self.tr("Delete All"), self)

        downloading_layout = QHBoxLayout(downloading_widget)
        downloading_layout.setContentsMargins(0, 0, 0, 0)
        downloading_layout.addStretch()
        downloading_layout.addWidget(self.search_downloading_list_box)
        downloading_layout.addWidget(self.filter_downloading_list_btn)
        downloading_layout.addWidget(self.sort_downloading_list_btn)
        downloading_layout.addWidget(self.open_folder_1_btn)
        downloading_layout.addWidget(separator_1)
        downloading_layout.addWidget(self.start_all_btn)
        downloading_layout.addWidget(self.pause_all_btn)
        downloading_layout.addWidget(self.delete_all_btn)

        completed_widget = QWidget()
        completed_widget.setContentsMargins(0, 0, 0, 0)

        self.search_completed_list_box = self._create_search_box()

        self.filter_completed_list_btn = ToggleToolButton(FluentIcon.FILTER, self)
        self.filter_completed_list_btn.setToolTip(self.tr("Filter"))

        self.sort_completed_list_btn = ToolButton(ExtendedFluentIcon.SORT, self)
        self.sort_completed_list_btn.setToolTip(self.tr("Sort"))

        self.open_folder_2_btn = ToolButton(FluentIcon.FOLDER, self)
        self.open_folder_2_btn.setToolTip(self.tr("Open Download Directory"))

        separator_2 = Separator(self, alpha = 50)

        self.clear_all_btn = PushButton(ExtendedFluentIcon.CLEAR, self.tr("Clear All"))
        self.clear_all_btn.setMinimumWidth(110)

        completed_layout = QHBoxLayout(completed_widget)
        completed_layout.setContentsMargins(0, 0, 0, 0)
        completed_layout.addStretch()
        completed_layout.addWidget(self.search_completed_list_box)
        completed_layout.addWidget(self.filter_completed_list_btn)
        completed_layout.addWidget(self.sort_completed_list_btn)
        completed_layout.addWidget(self.open_folder_2_btn)
        completed_layout.addWidget(separator_2)
        completed_layout.addWidget(self.clear_all_btn)

        self.addWidget(downloading_widget)
        self.addWidget(completed_widget)

        self.search_box_layout_list = [
            (downloading_layout, self.search_downloading_list_box),
            (completed_layout, self.search_completed_list_box)
        ]

        self.connect_signals()

    def _create_search_box(self):
        search_box = ExpandableSearchBox(self)
        search_box.setPlaceholderText(self.tr("Search"))

        return search_box

    def resizeEvent(self, e):
        super().resizeEvent(e)

        self._update_search_box_mode()

    def _update_search_box_mode(self):
        # 本控件占满 Pivot 右侧的全部宽度（见 DownloadInterface），减去搜索框以外的控件与间距，
        # 剩下的就是搜索框能用的空间。两页宽度相同，不在当前页的那个也一并更新，切过去时不会先跳一下
        for layout, search_box in self.search_box_layout_list:
            others_width = layout.sizeHint().width() - search_box.sizeHint().width()

            search_box.setAvailableWidth(self.width() - others_width)

    def connect_signals(self):
        self.open_folder_1_btn.clicked.connect(self.on_open_download_directory)
        self.open_folder_2_btn.clicked.connect(self.on_open_download_directory)

        self.filter_downloading_list_btn.clicked.connect(self.on_show_downloading_list_filter_flyout)
        self.filter_completed_list_btn.clicked.connect(self.on_show_completed_list_filter_flyout)

        self.sort_downloading_list_btn.clicked.connect(self.on_show_downloading_list_sort_flyout)
        self.sort_completed_list_btn.clicked.connect(self.on_show_completed_list_sort_flyout)

    def on_show_downloading_list_sort_flyout(self):
        sort_by_key_dict = {
            self.tr("Creation Time"): "created_time",
            self.tr("Title"): "show_title",
            self.tr("File Size"): "file_size",
            self.tr("Download Progress"): "progress"
        }

        self._show_sort_flyout(
            sort_by_key_dict,
            signal_bus.download.sort_downloading_list.emit,
            self.download_interface.downloading_list_view.sort_by_key,
            self.download_interface.downloading_list_view.sort_ascending,
            self.sort_downloading_list_btn
        )

    def on_show_completed_list_sort_flyout(self):
        sort_by_key_dict = {
            self.tr("Completion Time"): "completed_time",
            self.tr("Title"): "show_title",
            self.tr("File Size"): "file_size"
        }

        self._show_sort_flyout(
            sort_by_key_dict,
            signal_bus.download.sort_completed_list.emit,
            self.download_interface.completed_list_view.sort_by_key,
            self.download_interface.completed_list_view.sort_ascending,
            self.sort_completed_list_btn
        )

    def _show_sort_flyout(self, sort_by_key_dict, trigger_signal_func, sort_by_key, ascending, target):
        view = SortFlyoutWidget(self, sort_by_key_dict, trigger_signal_func, sort_by_key, ascending)

        flyout = Flyout.make(
            view = view,
            target = target,
            parent = self,
            aniType = FlyoutAnimationType.DROP_DOWN,
            isDeleteOnClose = False
        )

        view.closed.connect(flyout.fadeOut)

    def on_show_downloading_list_filter_flyout(self):
        # 按用户能分辨的阶段归组，而不是逐个列出 DownloadStatus：解析中一闪而过，
        # 合并 / 转换 / 附加处理在用户看来都是「下载完在收尾」
        status_group_dict = {
            self.tr("Downloading"): frozenset({DownloadStatus.DOWNLOADING, DownloadStatus.PARSING}),
            self.tr("Waiting"): frozenset({DownloadStatus.QUEUED, DownloadStatus.FFMPEG_QUEUED}),
            self.tr("Paused"): frozenset({DownloadStatus.PAUSED}),
            self.tr("Processing"): frozenset({DownloadStatus.MERGING, DownloadStatus.CONVERTING, DownloadStatus.ADDITIONAL_PROCESSING}),
            self.tr("Failed"): frozenset({DownloadStatus.FAILED, DownloadStatus.FFMPEG_FAILED, DownloadStatus.INVALID})
        }

        self._show_filter_flyout(
            self.download_interface.downloading_list_view,
            status_group_dict,
            self.filter_downloading_list_btn
        )

    def on_show_completed_list_filter_flyout(self):
        # 已完成列表里只有一种状态，不提供状态筛选
        self._show_filter_flyout(
            self.download_interface.completed_list_view,
            None,
            self.filter_completed_list_btn
        )

    def _show_filter_flyout(self, list_view, status_group_dict, target: ToggleToolButton):
        def trigger_signal_func(statuses: set, media_types: set):
            list_view.setStatusFilter(statuses)
            list_view.setMediaTypeFilter(media_types)

        def update_button_state():
            # 按钮的选中态只表示「有状态 / 类型筛选在生效」，不随点击翻转。
            # 搜索框里的文字一眼就看得见，不算在内
            target.setChecked(bool(list_view.status_filter or list_view.media_type_filter))

        # ToggleToolButton 被点击时自己会先翻转一次，这里立即纠正回来
        update_button_state()

        view = FilterFlyoutWidget(
            self, status_group_dict, get_media_type_group_dict(), trigger_signal_func,
            list_view.status_filter, list_view.media_type_filter
        )

        view.changed.connect(update_button_state)

        Flyout.make(
            view = view,
            target = target,
            parent = self,
            aniType = FlyoutAnimationType.DROP_DOWN
        )

    def on_open_download_directory(self):    
        Directory.open_directory_in_explorer(config.get(config.download_path))
