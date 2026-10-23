from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QWidget
from PySide6.QtCore import QTimer

from qfluentwidgets import Pivot, PopUpAniStackedWidget

from gui.component.download_list import TopStackedWidget, DownloadListView
from gui.component.download_list.pagination_bar import PaginationBar
from gui.component.widget.pivot import PivotItem

from util.download.task.query_worker import QueryWorker
from util.download.task.manager import task_manager
from util.download.task.info import TaskInfo

from util.common.enum import ToastNotificationCategory
from util.common.signal_bus import signal_bus
from util.common.config import config
from util.thread.async_ import AsyncTask

import logging

logger = logging.getLogger(__name__)


class DownloadInterface(QFrame):
    SEARCH_DEBOUNCE_MS = 300

    def __init__(self, parent = None):
        super().__init__(parent = parent)

        self.setObjectName("DownloadInterface")

        # 已完成列表分页状态
        self._completed_page = 0
        self._completed_page_size = PaginationBar.DEFAULT_PAGE_SIZE
        self._completed_total = 0
        self._completed_keyword = ""
        self._pending_search_text = ""

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._on_search_timeout)

        self.init_UI()

        self.get_tasks()

    def init_UI(self):
        self.pivot = Pivot(self)

        self.list_stacked_widget = PopUpAniStackedWidget(self)
        self.list_stacked_widget.setContentsMargins(0, 10, 0, 10)

        self.top_stacked_widget = TopStackedWidget(self)

        self.downloading_list_view = DownloadListView(self)
        self.downloading_list_view.setEmptyTextTip(self.tr("No downloads in progress"))
        self.downloading_list_view.setAutoManageConcurrentTasks(True)
        self.downloading_list_view.setAutoUpdateCountBadge(True)
        self.downloading_list_view.connectUpdateDataSignal()
        self.downloading_list_view.enableSorting(
            config.get(config.downloading_list_sort_by),
            config.get(config.downloading_list_sort_ascending)
        )

        self.completed_list_view = DownloadListView(self)
        self.completed_list_view.setEmptyTextTip(self.tr("No completed downloads"))
        # 分页模式：不调 enableSorting / setFilterText，排序与过滤由数据库负责。
        # 排序状态由本类注入，供顶栏排序浮窗读取当前值
        self.completed_list_view.setPaginationSortState(
            config.get(config.completed_list_sort_by),
            config.get(config.completed_list_sort_ascending)
        )

        # 已完成页容器：列表 + 分页条
        completed_container = QWidget(self)
        completed_container.setObjectName("completed")

        completed_layout = QVBoxLayout(completed_container)
        completed_layout.setContentsMargins(0, 0, 0, 0)
        completed_layout.addWidget(self.completed_list_view, 1)
        completed_layout.addWidget(self._build_pagination_bar())

        top_layout = QHBoxLayout()
        top_layout.addWidget(self.pivot)
        # 顶栏占满 Pivot 右侧的全部宽度（各页内部自带左侧弹簧，按钮仍靠右），
        # 这样它才知道还剩多少空间，决定搜索框是常驻显示还是收成按钮
        top_layout.addWidget(self.top_stacked_widget, 1)

        self.addSubInterface(self.downloading_list_view, "downloading", self.tr("Downloading"), 0)
        self.addSubInterface(completed_container, "completed", self.tr("Completed"), 1)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 15, 25, 15)
        main_layout.addLayout(top_layout)
        main_layout.addWidget(self.list_stacked_widget)

        self.pivot.setCurrentItem("downloading")

        self.connect_signals()

    def _build_pagination_bar(self):
        # parent_window 供 Pager 的跳转对话框作父窗口
        self.completed_pagination = PaginationBar(self, parent_window = self.window())
        self.completed_pagination.pageChanged.connect(self._on_completed_page_changed)
        self.completed_pagination.pageSizeChanged.connect(self._on_completed_page_size_changed)

        return self.completed_pagination

    def connect_signals(self):
        signal_bus.download.add_to_downloading_list.connect(self.downloading_list_view.addTask)
        signal_bus.download.auto_manage_concurrent_downloads.connect(self.downloading_list_view._schedule_auto_manage_concurrent_downloads)

        signal_bus.download.remove_from_downloading_list.connect(self.downloading_list_view.removeTask)
        signal_bus.download.remove_from_completed_list.connect(self.completed_list_view.removeTask)

        signal_bus.download.sort_downloading_list.connect(self.on_sort_downloading_list)
        signal_bus.download.sort_completed_list.connect(self.on_sort_completed_list)

        signal_bus.download.add_to_completed_list.connect(self._on_task_added_to_completed)
        self.completed_list_view.taskRemoved.connect(self._on_completed_task_removed)

        self.top_stacked_widget.start_all_btn.clicked.connect(self.downloading_list_view._model.batchStart)
        self.top_stacked_widget.pause_all_btn.clicked.connect(self.downloading_list_view._model.batchPause)
        self.top_stacked_widget.delete_all_btn.clicked.connect(self.downloading_list_view.batch_cancel)
        self.top_stacked_widget.clear_all_btn.clicked.connect(self._clear_all_completed)

        self.top_stacked_widget.search_downloading_list_box.textChanged.connect(self.downloading_list_view.setFilterText)
        self.top_stacked_widget.search_completed_list_box.textChanged.connect(self._on_completed_search_changed)

    def on_sort_downloading_list(self, key: str, ascending: bool):
        self._save_sort_preference(
            config.downloading_list_sort_by,
            config.downloading_list_sort_ascending,
            key,
            ascending
        )
        self.downloading_list_view._model.sortBy(key, ascending)

    def on_sort_completed_list(self, key: str, ascending: bool):
        self._save_sort_preference(
            config.completed_list_sort_by,
            config.completed_list_sort_ascending,
            key,
            ascending
        )

        self.completed_list_view.setPaginationSortState(key, ascending)

        self._completed_page = 0
        self._load_completed_page()

    def _save_sort_preference(self, key_item, ascending_item, key: str, ascending: bool):
        config.set(key_item, key, save = False)
        config.set(ascending_item, ascending, save = False)
        config.save()

    def addSubInterface(self, widget: QWidget, objectName: str, text: str, index):
        def onClick():
            self.list_stacked_widget.setCurrentWidget(widget)
            self.top_stacked_widget.setCurrentIndex(index)

        widget.setObjectName(objectName)
        self.list_stacked_widget.addWidget(widget)

        item = PivotItem(text = text, parent = self.pivot)
        item.setMinimumWidth(110)
        item.setFontSize(15)

        item = self.pivot.insertWidget(-1, objectName, item, onClick)

    def get_tasks(self):
        # 从数据库中查询下载任务，并添加到列表中
        worker = QueryWorker()
        worker.success.connect(self.on_query_success)
        worker.error.connect(self.on_query_error)

        AsyncTask.run(worker)

        self._load_completed_page()

    def on_query_success(self, downloading_tasks: list[TaskInfo], completed_tasks: list[TaskInfo]):
        self.downloading_list_view._beginAddQueriedTasks()
        self.downloading_list_view.addTask(downloading_tasks)
        self.downloading_list_view._endAddQueriedTasks()

    def on_query_error(self, error_message: str):
        signal_bus.toast.show_long_message.emit(
            ToastNotificationCategory.ERROR,
            self.tr("Failed to query download tasks"),
            error_message
        )

    # ---------- 已完成列表分页（同步执行） ----------

    def _load_completed_page(self):
        # 单次查询走 completed_time 索引只需几十毫秒，在 GUI 线程同步执行即可。
        # 每页条数、搜索关键词、排序方式任一变化都会调用本方法
        try:
            task_list = task_manager.query_completed_page(
                offset = self._completed_page * self._completed_page_size,
                limit = self._completed_page_size,
                order_by = config.get(config.completed_list_sort_by),
                ascending = config.get(config.completed_list_sort_ascending),
                keyword = self._completed_keyword
            )
            total = task_manager.count_completed(self._completed_keyword)

        except Exception as e:
            logger.exception("分页查询已完成任务失败")

            signal_bus.toast.show_long_message.emit(
                ToastNotificationCategory.ERROR,
                self.tr("Failed to query download tasks"),
                str(e)
            )

            return

        self._completed_total = total

        total_pages = max(1, (total + self._completed_page_size - 1) // self._completed_page_size)

        if self._completed_page >= total_pages:
            # 当前页越界（删除了最后一页的最后一条），回退到最后一页重查一次
            self._completed_page = total_pages - 1
            self._load_completed_page()

            return

        self.completed_list_view._source_model.setPageTasks(task_list)
        self.completed_pagination.setState(self._completed_page, total, self._completed_page_size)

    def _on_completed_page_changed(self, page: int):
        if page == self._completed_page:
            return

        self._completed_page = page
        self._load_completed_page()

    def _on_completed_page_size_changed(self, size: int):
        if size == self._completed_page_size:
            return

        self._completed_page_size = size
        self._completed_page = 0
        self._load_completed_page()

    def _on_completed_search_changed(self, text: str):
        self._search_timer.stop()
        self._pending_search_text = text
        self._search_timer.start(self.SEARCH_DEBOUNCE_MS)

    def _on_search_timeout(self):
        self._completed_keyword = self._pending_search_text.strip()
        self._completed_page = 0
        self._load_completed_page()

    def _on_task_added_to_completed(self, task_info: TaskInfo):
        order_by = config.get(config.completed_list_sort_by)
        ascending = config.get(config.completed_list_sort_ascending)

        if self._completed_page == 0 and not self._completed_keyword and order_by == "completed_time" and not ascending:
            self._load_completed_page()

        else:
            self._completed_total += 1
            self.completed_pagination.setState(self._completed_page, self._completed_total, self._completed_page_size)

    def _on_completed_task_removed(self, count: int):
        self._completed_total = max(0, self._completed_total - count)
        self._load_completed_page()

    def _clear_all_completed(self):
        task_manager.clear_completed()

        self._completed_total = 0
        self._completed_page = 0

        self.completed_list_view._source_model.setPageTasks([])
        self.completed_pagination.setState(0, 0, self._completed_page_size)