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
        self._completed_media_types = frozenset()      # 媒体类型筛选，空集表示不筛
        self._pending_search_text = ""

        self._search_timer = QTimer(self)
        self._search_timer.setSingleShot(True)
        self._search_timer.timeout.connect(self._on_search_timeout)

        self.init_UI()

        self.get_tasks()

    @property
    def completed_media_types(self) -> frozenset:
        # TopStackedWidget 的筛选按钮状态读这里
        return self._completed_media_types

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
        # 分页模式：不调 enableSorting / setFilterText / setMediaTypeFilter，
        # 排序与筛选全部由数据库负责。排序状态由本类注入，供顶栏排序浮窗读
        self.completed_list_view.setPaginationSortState(
            config.get(config.completed_list_sort_by),
            config.get(config.completed_list_sort_ascending)
        )

        completed_container = QWidget(self)
        completed_container.setObjectName("completed")

        completed_layout = QVBoxLayout(completed_container)
        completed_layout.setContentsMargins(0, 0, 0, 0)
        completed_layout.addWidget(self.completed_list_view, 1)
        completed_layout.addWidget(self._build_pagination_bar())

        top_layout = QHBoxLayout()
        top_layout.addWidget(self.pivot)
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
        self.completed_list_view.taskPermanentlyDeleted.connect(self._on_completed_task_permanently_deleted)

        # 已完成列表的媒体筛选：TopStackedWidget 不再走 proxy，改为发信号下推 SQL
        self.top_stacked_widget.completed_list_filter_changed.connect(self._on_completed_filter_changed)

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

        # 排序变化保持原页码，越界时由 _load_completed_page 内部回退。
        # 总数不随排序变化，传 refresh_total=False 省掉一次全表 count ——
        # 媒体筛选下的 count 与列表查询是同一份开销（各扫一遍全表）
        self._load_completed_page(refresh_total = False)

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
        # 数据库升级失败时已完成列表全程为空，启动时提示一次，避免用户以为任务丢了。
        # 启动路径上此时 MainWindow 已建好、toast 信号已连，提示能正常显示
        if task_manager.db_manager.upgrade_failed:
            signal_bus.toast.show_long_message.emit(
                ToastNotificationCategory.ERROR,
                self.tr("Failed to upgrade completed task database"),
                self.tr("The completed list is unavailable in this session. Please check disk space and filesystem permissions, then restart the application.")
            )

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

    # ---------- 已完成列表分页 ----------

    def _load_completed_page(self, refresh_total: bool = True):
        # 单次查询走索引只需几十毫秒，在 GUI 线程同步执行即可。
        #
        # refresh_total=False 时复用缓存的 _completed_total，跳过 count 查询。
        # 翻页、排序切换、每页大小变化这几种操作的总数不会变，而媒体筛选下的
        # count 与列表查询是同一份开销（各扫一遍全表），跳过能省一半时间
        try:
            task_list = task_manager.query_completed_page(
                offset = self._completed_page * self._completed_page_size,
                limit = self._completed_page_size,
                order_by = config.get(config.completed_list_sort_by),
                ascending = config.get(config.completed_list_sort_ascending),
                keyword = self._completed_keyword,
                media_types = self._completed_media_types,
            )

            if refresh_total:
                total = task_manager.count_completed(self._completed_keyword, self._completed_media_types)

                self._completed_total = total
            else:
                total = self._completed_total

        except Exception as e:
            logger.exception("分页查询已完成任务失败")

            signal_bus.toast.show_long_message.emit(
                ToastNotificationCategory.ERROR,
                self.tr("Failed to query download tasks"),
                str(e)
            )

            return

        total_pages = max(1, (total + self._completed_page_size - 1) // self._completed_page_size)

        if self._completed_page >= total_pages:
            self._completed_page = total_pages - 1
            self._load_completed_page(refresh_total = refresh_total)

            return

        # 空列表时的提示靠 setFiltering 区分「无任务」与「无匹配」。
        # 关键词或媒体筛选任一存在都算「筛选生效」
        self.completed_list_view.setFiltering(
            bool(self._completed_keyword or self._completed_media_types)
        )
        self.completed_list_view._source_model.setPageTasks(task_list)
        self.completed_pagination.setState(self._completed_page, total, self._completed_page_size)

    def _on_completed_page_changed(self, page: int):
        if page == self._completed_page:
            return

        self._completed_page = page

        # 翻页不改变总数，跳过 count 查询
        self._load_completed_page(refresh_total = False)

    def _on_completed_page_size_changed(self, size: int):
        if size == self._completed_page_size:
            return

        # 新页中应包含原当前页的第一个条目
        first_index = self._completed_page * self._completed_page_size
        new_page = first_index // size

        self._completed_page_size = size
        self._completed_page = new_page

        # 每页大小变化不改变总数，跳过 count 查询
        self._load_completed_page(refresh_total = False)

    def _on_completed_search_changed(self, text: str):
        self._search_timer.stop()
        self._pending_search_text = text
        self._search_timer.start(self.SEARCH_DEBOUNCE_MS)

    def _on_search_timeout(self):
        self._completed_keyword = self._pending_search_text.strip()

        # 搜索变化保持原页码，越界由 _load_completed_page 内部回退。
        # 关键词变化会改变总数，需要重新 count
        self._load_completed_page()

    def _on_completed_filter_changed(self, media_types: set):
        # TopStackedWidget 的筛选浮窗发出的媒体类型集合，直接下推 SQL
        self._completed_media_types = frozenset(media_types)

        # 筛选变化保持原页码，越界由 _load_completed_page 内部回退。
        # 媒体筛选变化会改变总数，需要重新 count
        self._load_completed_page()

    def _on_task_added_to_completed(self, task_info_list):
        # 无条件重载当前页，让页面内容随时反映最新状态。
        # 当前页码保持不变；保存/恢复滚动位置，避免新任务完成时列表跳回顶部。
        # QTimer.singleShot 的 context 传 self：控件先一步销毁时回调不再执行，
        # 避免打到已经析构的 verticalScrollBar() 上。
        # 新任务会改变总数，需要重新 count
        scroll_value = self.completed_list_view.verticalScrollBar().value()

        self._load_completed_page()

        QTimer.singleShot(0, self, lambda: self.completed_list_view.verticalScrollBar().setValue(scroll_value))

    def _on_completed_task_removed(self, count: int):
        # 只更新总数，不重载。
        # - redownload 路径下库里记录还在（recreate 异步未完成），此刻重载会让
        #   刚移除的行又出现
        # - 单条删除后当前页少一行，下次翻页自然补齐
        # - 删空当前页的补位统一由 task_permanently_deleted 处理：
        #   若这里也重载，删除成功后 removeTasks 与 task_permanently_deleted
        #   会连续触发两次重载（两次查库 + 两次 reset），滚动位置也会闪
        self._completed_total = max(0, self._completed_total - count)
        self.completed_pagination.setState(self._completed_page, self._completed_total, self._completed_page_size)

    def _on_completed_task_permanently_deleted(self, count: int):
        # 数据库已落盘的真正删除，可以安全重载补位。
        # 保存/恢复滚动位置，避免删除后跳回顶部。
        # QTimer.singleShot 的 context 传 self，理由同上。
        # 删除会改变总数，需要重新 count
        scroll_value = self.completed_list_view.verticalScrollBar().value()

        self._load_completed_page()

        QTimer.singleShot(0, self, lambda: self.completed_list_view.verticalScrollBar().setValue(scroll_value))

    def _clear_all_completed(self):
        has_filter = bool(self._completed_keyword or self._completed_media_types)

        if has_filter:
            # 关键词和媒体筛选都下推到 SQL，两者是 AND 关系，与旧版
            # proxy 模式下 batch_cancel 的 _batchTargets 语义一致
            if task_manager.delete_completed_by_filter(self._completed_keyword, self._completed_media_types):
                self._load_completed_page()

            else:
                signal_bus.toast.show_long_message.emit(
                    ToastNotificationCategory.ERROR,
                    self.tr("Failed to clear completed tasks"),
                    self.tr("The database write failed. Please try again.")
                )

            return

        if not task_manager.clear_completed():
            signal_bus.toast.show_long_message.emit(
                ToastNotificationCategory.ERROR,
                self.tr("Failed to clear completed tasks"),
                self.tr("The database write failed. Please try again.")
            )

            return

        self._completed_total = 0
        self._completed_page = 0

        self.completed_list_view._source_model.setPageTasks([])
        self.completed_pagination.setState(0, 0, self._completed_page_size)