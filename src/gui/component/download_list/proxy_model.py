from PySide6.QtCore import QModelIndex, Qt, QSortFilterProxyModel, QTimer
from PySide6.QtWidgets import QAbstractItemView

from util.download.task.info import TaskInfo
from util.common.signal_bus import signal_bus

from .item_delegate import get_media_type_key
from .model import DownloadListModel


class DownloadListProxyModel(QSortFilterProxyModel):
    def __init__(self, parent = None):
        super().__init__(parent)

        self._sorting = False
        self._sort_by_key = None
        self._ascending = True

        self._filter_text = ""
        self._filter_keywords: list[str] = []
        self._status_filter = None
        self._media_type_filter = None
        self._filter_refresh_pending = False
        self._sort_refresh_pending = False

        self._refresh_timer = QTimer(self)
        self._refresh_timer.setSingleShot(True)
        self._refresh_timer.timeout.connect(self._flushPendingRefresh)

        self.setDynamicSortFilter(False)

    def sourceModel(self) -> DownloadListModel:
        return super().sourceModel()

    def _source(self) -> DownloadListModel:
        return self.sourceModel()

    def _matchesFilter(self, task_info: TaskInfo):
        if self._status_filter and task_info.Download.status not in self._status_filter:
            return False

        if self._media_type_filter and get_media_type_key(task_info) not in self._media_type_filter:
            return False

        if self._filter_keywords:
            searchable_text = self._getSearchableText(task_info)

            # 多个关键词按空格分开、同时命中才算匹配：「UP主名 合集名」这种组合用起来最顺手
            if not all(keyword in searchable_text for keyword in self._filter_keywords):
                return False

        return True

    def _getSearchableText(self, task_info: TaskInfo):
        # 只收建任务时就定下来、用户认得出的字段。task_id 是内部哈希，info_label / status_label
        # 是随界面语言与下载进度变化的展示文案（「3 秒后重试」），搜得到反而让结果忽隐忽现
        episode = task_info.Episode

        return " ".join([
            task_info.Basic.show_title or "",
            task_info.File.name or "",
            episode.uploader or "",
            episode.bvid or "",
            episode.parent_title or "",
            episode.collection_title or "",
            episode.series_title or "",
            episode.season_title or "",
            episode.favorites_name or "",
        ]).casefold()

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex):
        source = self._source()

        if not source:
            return False

        task_info: TaskInfo = source.index(source_row, 0, source_parent).data(Qt.ItemDataRole.UserRole)

        if task_info is None:
            return False

        return self._matchesFilter(task_info)

    def _scheduleRefresh(self, refresh_filter = False, refresh_sort = False):
        self._filter_refresh_pending |= refresh_filter
        self._sort_refresh_pending |= refresh_sort

        if not self._refresh_timer.isActive():
            self._refresh_timer.start(50)

    def _flushPendingRefresh(self):
        refresh_filter = self._filter_refresh_pending
        refresh_sort = self._sort_refresh_pending

        self._filter_refresh_pending = False
        self._sort_refresh_pending = False

        if refresh_filter:
            # invalidateFilter / invalidateRowsFilter 在 Qt 6.10 起弃用。begin 本应在改筛选参数之前调，
            # 但参数改动都经过去抖，到这里早已改完；begin 只是确保映射表已建好，成对紧挨着调用效果相同
            self.beginFilterChange()
            self.endFilterChange(QSortFilterProxyModel.Direction.Rows)

        # 过滤刷新后也要重排：dynamicSortFilter 关着，重新放出来的行会被接在末尾，
        # 而不是插回排序后的位置（与 _applyCurrentSort 说的追加问题同源）
        if (refresh_filter or refresh_sort) and self._sorting and self._sort_by_key:
            order = Qt.SortOrder.AscendingOrder if self._ascending else Qt.SortOrder.DescendingOrder
            self.sort(0, order)

    def lessThan(self, left: QModelIndex, right: QModelIndex):
        left_task: TaskInfo = left.data(Qt.ItemDataRole.UserRole)
        right_task: TaskInfo = right.data(Qt.ItemDataRole.UserRole)

        if not left_task or not right_task or not self._sort_by_key:
            return super().lessThan(left, right)

        match self._sort_by_key:
            case "created_time":
                return (left_task.Basic.created_time or 0) < (right_task.Basic.created_time or 0)

            case "completed_time":
                return (left_task.Basic.completed_time or 0) < (right_task.Basic.completed_time or 0)

            case "show_title":
                return (left_task.Basic.show_title or "").casefold() < (right_task.Basic.show_title or "").casefold()

            case "file_size":
                return (left_task.Download.total_size or 0) < (right_task.Download.total_size or 0)

            case "progress":
                return (left_task.Download.progress or 0) < (right_task.Download.progress or 0)

        return super().lessThan(left, right)

    def rowCount(self, parent = QModelIndex()):
        return super().rowCount(parent)

    def data(self, index: QModelIndex, role = Qt.ItemDataRole.DisplayRole):
        return super().data(index, role)

    def queryRowCover(self, cover_id: str, cover_url: str, row: int, device_pixel_ratio: float):
        source = self._source()

        if not source:
            return None, True

        proxy_index = self.index(row, 0)
        source_index = self.mapToSource(proxy_index)

        if not source_index.isValid():
            return source.queryRowCover(None, None, 0, device_pixel_ratio)

        return source.queryRowCover(cover_id, cover_url, source_index.row(), device_pixel_ratio)

    def updateRowCover(self, cover_id: str, image):
        source = self._source()

        if source:
            source.updateRowCover(cover_id, image)

    def setQueryCoverParam(self, param: dict):
        source = self._source()

        if source:
            source.setQueryCoverParam(param)

    def getRow(self, task_info: TaskInfo):
        source = self._source()

        if not source:
            return -1

        source_row = source.getRow(task_info)

        if source_row == -1:
            return -1

        proxy_index = self.mapFromSource(source.index(source_row, 0))

        if not proxy_index.isValid():
            return -1

        return proxy_index.row()

    def appendRow(self, task_info: TaskInfo):
        source = self._source()

        if source:
            source.appendRow(task_info)

            self._applyCurrentSort()

    def appendRows(self, task_info_list: list[TaskInfo]):
        source = self._source()

        if source:
            source.appendRows(task_info_list)

            self._applyCurrentSort()

    def _applyCurrentSort(self):
        """
        追加之后按当前排序方式重排一次

        dynamicSortFilter 关着（进度更新太频繁，靠 _scheduleRefresh 去抖），代价是新插入的
        行不会被排进正确位置：Qt 只把这一批行在**批内**排好，整批接在末尾。启动时列表是空的、
        任务一次性载入，所以看着正常；之后新建的任务、刚下载完移进"已完成"的任务都会停在最底下，
        降序时尤其显眼，用户得手动再点一次排序才归位。

        这里同步排而不走去抖：任务是成批追加的，一批排一次，代价不大；延后 50 毫秒反而会让
        新任务先在末尾闪一下再跳走
        """
        if self._sorting and self._sort_by_key:
            order = Qt.SortOrder.AscendingOrder if self._ascending else Qt.SortOrder.DescendingOrder

            self.sort(0, order)

    def removeRow(self, row, parent = QModelIndex()):
        source = self._source()

        if not source or not (0 <= row < self.rowCount(parent)):
            return False

        proxy_index = self.index(row, 0, parent)
        source_index = self.mapToSource(proxy_index)

        if not source_index.isValid():
            return False

        return source.removeRow(source_index.row())

    def removeTask(self, task_info: TaskInfo):
        source = self._source()

        if not source:
            return False

        source_row = source.getRow(task_info)

        if source_row == -1:
            return False

        return source.removeRow(source_row)

    def removeTasks(self, task_info_list: list[TaskInfo]):
        source = self._source()

        if source:
            source.removeTasks(task_info_list)

    def togglePauseResume(self, task_info: TaskInfo):
        source = self._source()

        if source:
            source.togglePauseResume(task_info)

            self._onStatusChanged()

    def cancelDownload(self, task_info: TaskInfo):
        source = self._source()

        if source:
            source.cancelDownload(task_info)

    def _onStatusChanged(self):
        """
        经由本代理发起、会直接改写任务状态的操作，结束后补一次过滤

        这些操作里源模型只调自己的 onUpdateData，不经过 update_downloading_item 信号，
        本类的 onUpdateData 收不到：按「已暂停」筛选时点「全部开始」，任务明明已经排上队，
        却要等到下载器下一次上报才从列表里消失
        """
        if self._status_filter:
            self._scheduleRefresh(refresh_filter = True)

    def visibleTasks(self):
        return [self.index(row, 0).data(Qt.ItemDataRole.UserRole) for row in range(self.rowCount())]

    def _batchTargets(self):
        """
        批量操作的作用范围：筛选生效时只取当前看得见的任务，否则为 None 表示整个列表

        顶栏的「全部删除」「全部清除」没有二次确认。筛选之后用户眼里的「全部」就是眼前这几条，
        若仍按整个列表执行，一键会删掉一批根本没显示出来的任务，且无从撤销
        """
        if self.isFiltering():
            return self.visibleTasks()

        return None

    def batchStart(self):
        source = self._source()

        if source:
            source.batchStart(self._batchTargets())

            self._onStatusChanged()

    def batchPause(self):
        source = self._source()

        if source:
            source.batchPause(self._batchTargets())

            self._onStatusChanged()

    def batch_cancel(self):
        source = self._source()

        if source:
            source.batch_cancel(self._batchTargets())

    def manageConcurrentDownloads(self):
        source = self._source()

        if source:
            source.manageConcurrentDownloads()

    def manageConcurrentMerges(self):
        source = self._source()

        if source:
            source.manageConcurrentMerges()

    def redownload(self, task_info: TaskInfo):
        source = self._source()

        if source:
            source.redownload(task_info)

            self._onStatusChanged()

    def connectUpdateDataSignal(self):
        signal_bus.download.update_downloading_item.connect(self.onUpdateData)

    def onUpdateData(self, task_info: TaskInfo):
        row = self.getRow(task_info)

        if row != -1 and self.isRowInVisibleArea(row):
            model_index = self.index(row, 0)
            self.dataChanged.emit(model_index, model_index)

        # 进度更新里会变的只有状态，类型与可搜索的字段在建任务时就定了，
        # 只有按状态筛选时才需要跟着重新过滤
        if self._status_filter:
            self._scheduleRefresh(refresh_filter = True)

        if self._sort_by_key in {"file_size", "progress"}:
            self._scheduleRefresh(refresh_sort = True)

    def isRowInVisibleArea(self, row: int):
        view: QAbstractItemView = self.parent()

        if view and view.isVisible():
            viewport = view.viewport()
            item_rect = view.visualRect(self.index(row, 0))

            return viewport.rect().intersects(item_rect)

        return False

    def sortBy(self, key: str, ascending: bool = True):
        if not self._sorting:
            return

        self._sort_by_key = key
        self._ascending = ascending

        order = Qt.SortOrder.AscendingOrder if ascending else Qt.SortOrder.DescendingOrder

        self.sort(0, order)

    def enableSorting(self, default_key: str, ascending: bool = True):
        self._sorting = True
        self._sort_by_key = default_key
        self._ascending = ascending

        self.sortBy(default_key, ascending)

    def setFilterText(self, text: str):
        self._filter_text = text.strip()
        self._filter_keywords = self._filter_text.casefold().split()
        self._scheduleRefresh(refresh_filter = True)

    def setStatusFilter(self, statuses):
        self._status_filter = set(statuses) if statuses else None
        self._scheduleRefresh(refresh_filter = True)

    def setMediaTypeFilter(self, media_types):
        self._media_type_filter = set(media_types) if media_types else None
        self._scheduleRefresh(refresh_filter = True)

    def clearFilter(self):
        self._filter_text = ""
        self._filter_keywords = []
        self._status_filter = None
        self._media_type_filter = None
        self._scheduleRefresh(refresh_filter = True)

    def isFiltering(self):
        return bool(self._filter_keywords or self._status_filter or self._media_type_filter)

    @property
    def status_filter(self):
        return frozenset(self._status_filter or ())

    @property
    def media_type_filter(self):
        return frozenset(self._media_type_filter or ())