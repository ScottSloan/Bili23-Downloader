from PySide6.QtCore import QModelIndex, QTimer, Signal

from util.download.task.filter import get_media_type_key, get_searchable_text, matches_keywords, split_keywords
from util.download.task.manager import task_manager
from util.download.task.info import TaskInfo
from util.thread.dispatcher import post_to_main_thread

from .model import DownloadListModel, SORT_KEY_FUNCS, nocase_key

from typing import List
import logging

logger = logging.getLogger(__name__)

class CompletedListModel(DownloadListModel):
    """
    已完成列表的源模型：按需从数据库分批读取，滚动到底再取下一批

    已完成的任务是长期累积的，攒到数万条后，启动时全量读出要反序列化几百 MB 的 JSON，
    常驻内存也随之膨胀。这里只读用户真正翻到的部分，排序、搜索与类型筛选都交给数据库执行
    （判定逻辑与下载中列表共用，见 util/download/task/filter.py）。

    读取在 TaskManager 的读线程上进行，结果投递回 GUI 线程。几个容易出错的地方：

    1. 分批用键集游标 (排序值, id) 而不是 OFFSET，见 db.query_completed_batch
    2. 每次重新读取（换排序、改筛选）都递增 _generation，迟到的旧结果直接丢弃
    3. 新完成的任务不能一律插进来：若它排在尚未读取的部分，之后翻到那里时数据库会再返回一次。
       以游标为界，排在游标之前的才插入内存，之后的留给下一批去读
    """
    BATCH_SIZE = 100

    # 新任务一律逐条二分插入。父类条数多时改走「接在末尾 + resort()」，而这里的 resort() 什么也不做
    # （顺序由数据库决定），那条路会把新任务留在末尾
    _INSERT_THRESHOLD = float("inf")

    # 改搜索词时去抖：每次读取在没有命中时要把整张表扫一遍，不必每敲一个字都查
    FILTER_DEBOUNCE_MS = 300

    loadFailed = Signal(str)

    def __init__(self, task_list: list, parent = None):
        super().__init__(task_list, parent)

        self._sort_key = "completed_time"
        self._ascending = False

        self._keywords: List[str] = []
        self._media_types = None

        self._started = False
        self._loading = False
        self._exhausted = False
        self._generation = 0

        # 上一批最后一行的 (排序值, id)，排序值已按 nocase_key 规整，可直接与内存中的排序键比较
        self._cursor = None

        # 读取进行中完成的任务先放这里，等这一批落定、游标更新后再判断要不要插入
        self._pending_tasks: List[TaskInfo] = []

        self._reload_timer = QTimer(self)
        self._reload_timer.setSingleShot(True)
        self._reload_timer.timeout.connect(self._reload)

    def setSortOrder(self, key: str, ascending: bool = True):
        self._sort_key_func = SORT_KEY_FUNCS.get(key)
        self._sort_reverse = not ascending

        self._sort_key = key
        self._ascending = ascending

        self._started = True

        self._reload_timer.stop()
        self._reload()

    def resort(self):
        # 顺序由数据库决定，内存里只有已读出的一部分，不能自行重排
        pass

    def setFilterText(self, text: str):
        keywords = split_keywords(text)

        if keywords != self._keywords:
            self._keywords = keywords

            self._scheduleReload(self.FILTER_DEBOUNCE_MS)

    def setMediaTypeFilter(self, media_types):
        media_types = frozenset(media_types) if media_types else None

        if media_types != self._media_types:
            self._media_types = media_types

            self._scheduleReload(0)

    def setStatusFilter(self, statuses):
        # 已完成列表里只有一种状态，不提供状态筛选
        pass

    def isFiltering(self):
        return bool(self._keywords or self._media_types)

    @property
    def status_filter(self):
        return frozenset()

    @property
    def media_type_filter(self):
        return frozenset(self._media_types or ())

    def canFetchMore(self, parent = QModelIndex()):
        if parent.isValid():
            return False

        return self._started and not self._loading and not self._exhausted

    def fetchMore(self, parent = QModelIndex()):
        if self.canFetchMore(parent):
            self._requestBatch(reset = False)

    def appendRows(self, task_info_list: List[TaskInfo]):
        # 只有新完成的任务会走到这里（下载完成后经 add_to_completed_list 加入）
        if self._loading:
            self._pending_tasks.extend(task_info_list)

            return

        self._insertNewTasks(task_info_list)

    def batch_cancel(self, task_list: List[TaskInfo] = None):
        if task_list is not None:
            super().batch_cancel(task_list)

            return

        # 「全部清除」作用于数据库里所有满足当前筛选的记录，而不只是已经读出来的那几批，
        # 与全部载入内存时的语义一致。已读出的行本就都满足当前筛选，一并移除即可
        task_manager.delete_completed_matching(self._keywords, self._media_types)

        # 满足条件的已全部删除，按当前条件再读也不会有结果；作废进行中的读取，免得删前的结果晚到又填回来
        self._generation += 1
        self._loading = False
        self._exhausted = True
        self._pending_tasks.clear()

        self.removeTasks(list(self._task_list))

    def _scheduleReload(self, delay: int):
        if self._started:
            self._reload_timer.start(delay)

    def _reload(self):
        self._generation += 1

        self._cursor = None
        self._exhausted = False

        # 读取进行中积压的新任务已经写进数据库，重新读取时自然会带上，不必再单独插入
        self._pending_tasks.clear()

        # 旧内容先留着，新结果到了再整体替换，避免列表先清空再填满地闪一下
        self._requestBatch(reset = True)

    def _requestBatch(self, reset: bool):
        self._loading = True

        task_manager.submit_read(
            self._loadInBackground,
            self._generation,
            reset,
            (self._sort_key, self._ascending, self.BATCH_SIZE, self._cursor, tuple(self._keywords), self._media_types)
        )

    def _loadInBackground(self, generation: int, reset: bool, params: tuple):
        # 运行在读线程上，只能读传进来的参数，不能碰 self 上的任何状态
        try:
            # 先等写线程上已排队的删除、归档落盘，否则刚删掉的记录可能又被读回来
            task_manager.wait_for_pending_writes()

            rows = task_manager.query_completed_batch(*params)

        except Exception as e:
            logger.exception("分批读取已完成的下载任务失败")

            post_to_main_thread(self._onBatchFailed, generation, str(e))

            return

        post_to_main_thread(self._onBatchLoaded, generation, reset, rows)

    def _onBatchFailed(self, generation: int, error_message: str):
        if generation != self._generation:
            return

        self._loading = False

        # 停在这里，不再自动重试：视图每次滚到底都会调 fetchMore，失败的查询会被反复触发
        self._exhausted = True

        self.loadFailed.emit(error_message)

    def _onBatchLoaded(self, generation: int, reset: bool, rows: list):
        if generation != self._generation:
            # 已被更新的读取取代。_loading 由那次读取负责清除
            return

        self._loading = False
        self._exhausted = len(rows) < self.BATCH_SIZE

        if rows:
            sort_value, row_id, _ = rows[-1]

            self._cursor = (nocase_key(sort_value) if isinstance(sort_value, str) else sort_value, row_id)

        task_info_list = [task_info for _, _, task_info in rows]

        if reset:
            self.beginResetModel()

            self._task_list[:] = task_info_list

            self.endResetModel()

            self._rebuild_row_index()

        else:
            # 读取期间刚插入内存的新任务，若恰好也落在这一批里，不要重复加入
            task_info_list = [task_info for task_info in task_info_list if self.getRow(task_info) == -1]

            if task_info_list:
                self._extendRows(task_info_list)

        pending, self._pending_tasks = self._pending_tasks, []

        self._insertNewTasks(pending)

    def _insertNewTasks(self, task_info_list: List[TaskInfo]):
        accepted = [
            task_info for task_info in task_info_list
            if self.getRow(task_info) == -1 and self._matchesFilter(task_info) and self._isWithinLoadedRange(task_info)
        ]

        if accepted:
            super().appendRows(accepted)

    def _matchesFilter(self, task_info: TaskInfo):
        if self._media_types and get_media_type_key(task_info) not in self._media_types:
            return False

        if self._keywords and not matches_keywords(get_searchable_text(task_info), self._keywords):
            return False

        return True

    def _isWithinLoadedRange(self, task_info: TaskInfo):
        """
        新完成的任务是否排在已读取的范围内（游标之前）

        新任务在数据库里的 id 一定比游标大：降序时键值相等也排在游标之前，升序时则排在之后
        """
        if self._exhausted:
            return True

        if self._cursor is None or self._sort_key_func is None:
            # 还没读出过任何一批，之后的读取自然会带上它
            return False

        key = self._sort_key_func(task_info)
        cursor_key = self._cursor[0]

        return key < cursor_key if self._ascending else key >= cursor_key
