from PySide6.QtCore import QModelIndex, Qt, QSortFilterProxyModel
from PySide6.QtWidgets import QAbstractItemView

from util.download import TaskInfo
from util.common import signal_bus

from .model import DownloadListModel


class DownloadListProxyModel(QSortFilterProxyModel):
    def __init__(self, parent = None):
        super().__init__(parent)

        self._sorting = False
        self._sort_by_key = None
        self._ascending = True

        self._filter_text = ""
        self._status_filter = None

        self.setDynamicSortFilter(True)

    def sourceModel(self) -> DownloadListModel:
        return super().sourceModel()

    def _source(self) -> DownloadListModel:
        return self.sourceModel()

    def _matchesFilter(self, task_info: TaskInfo):
        if self._status_filter and task_info.Download.status not in self._status_filter:
            return False

        if self._filter_text:
            keyword = self._filter_text.casefold()
            searchable_text = " ".join([
                str(task_info.Basic.task_id),
                task_info.Basic.show_title or "",
                task_info.Download.info_label or "",
                task_info.Download.status_label or "",
            ]).casefold()

            if keyword not in searchable_text:
                return False

        return True

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex):
        source = self._source()

        if not source:
            return False

        task_info: TaskInfo = source.index(source_row, 0, source_parent).data(Qt.ItemDataRole.UserRole)

        if task_info is None:
            return False

        return self._matchesFilter(task_info)

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

    def queryRowCover(self, cover_id: str, cover_url: str, row: int):
        source = self._source()

        if not source:
            return None, True

        proxy_index = self.index(row, 0)
        source_index = self.mapToSource(proxy_index)

        if not source_index.isValid():
            return source.queryRowCover(None, None, 0)

        return source.queryRowCover(cover_id, cover_url, source_index.row())

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

    def appendRows(self, task_info_list: list[TaskInfo]):
        source = self._source()

        if source:
            source.appendRows(task_info_list)

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

    def togglePauseResume(self, task_info: TaskInfo):
        source = self._source()

        if source:
            source.togglePauseResume(task_info)

    def cancelDownload(self, task_info: TaskInfo):
        source = self._source()

        if source:
            source.cancelDownload(task_info)

    def batchStart(self):
        source = self._source()

        if source:
            source.batchStart()

    def batchPause(self):
        source = self._source()

        if source:
            source.batchPause()

    def batch_cancel(self):
        source = self._source()

        if source:
            source.batch_cancel()

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

    def connectUpdateDataSignal(self):
        signal_bus.download.update_downloading_item.connect(self.onUpdateData)

    def onUpdateData(self, task_info: TaskInfo):
        self.invalidateFilter()

        row = self.getRow(task_info)

        if row == -1:
            return

        if self.isRowInVisibleArea(row):
            model_index = self.index(row, 0)
            self.dataChanged.emit(model_index, model_index)

    def isRowInVisibleArea(self, row: int):
        view: QAbstractItemView = self.parent()

        if view:
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

    def enableSorting(self, default_key: str):
        self._sorting = True
        self._sort_by_key = default_key
        self._ascending = True

        self.sortBy(default_key, True)

    def setFilterText(self, text: str):
        self._filter_text = text.strip()
        self.invalidateFilter()

    def setStatusFilter(self, statuses):
        self._status_filter = set(statuses) if statuses else None
        self.invalidateFilter()

    def clearFilter(self):
        self._filter_text = ""
        self._status_filter = None
        self.invalidateFilter()
