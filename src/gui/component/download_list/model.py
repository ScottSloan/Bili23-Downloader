from PySide6.QtCore import QModelIndex, Qt, QSize
from PySide6.QtWidgets import QAbstractItemView

from util.download.downloader.manager import downloader_manager
from util.download.task.manager import task_manager
from util.download.task.info import TaskInfo
from util.common.signal_bus import signal_bus
from util.common.enum import DownloadStatus
from util.common.config import config

from ..view_model import CoverQueryModelBase

from typing import List
import string

_ASCII_LOWER = str.maketrans(string.ascii_uppercase, string.ascii_lowercase)

def nocase_key(text: str):
    """
    与 SQLite 的 NOCASE 排序规则等价的排序键：只折叠 ASCII 字母，其余字符按码位比较

    已完成列表的排序交给数据库执行（见 CompletedListModel），新完成的任务却是在内存里插入的。
    两边的比较规则必须一致，否则新任务会插错位置，分批读取时还可能漏掉或重复。
    不用 casefold() 的代价是 ß、İ 这类非 ASCII 字母不再折叠大小写，中文标题不受影响
    """
    return (text or "").translate(_ASCII_LOWER)

# 排序键 → 取值函数，与顶栏排序浮窗里的选项一一对应
SORT_KEY_FUNCS = {
    "created_time": lambda task_info: task_info.Basic.created_time or 0,
    "completed_time": lambda task_info: task_info.Basic.completed_time or 0,
    "show_title": lambda task_info: nocase_key(task_info.Basic.show_title),
    "file_size": lambda task_info: task_info.Download.total_size or 0,
    "progress": lambda task_info: task_info.Download.progress or 0,
}

class DownloadListModel(CoverQueryModelBase):
    # 一次追加不超过这么多条时逐条二分插入，否则接在末尾后整体重排一次。
    # 逐条插入每条都要挪动列表并发一次 rowsInserted，条数多了不如一次 layoutChanged
    _INSERT_THRESHOLD = 64

    def __init__(self, task_list: list, parent = None):
        super().__init__(parent)

        self._cover_size = QSize(144, 80)
        self._task_list: List[TaskInfo] = task_list

        self._row_by_task_id: dict[str, int] = {}
        self._managing_concurrent = False
        self._managing_merges = False

        # 排序放在源模型里做，而不是交给 QSortFilterProxyModel.sort()。
        # 代理排序每比较一次就要回调两次 Python 的 lessThan / data()，已完成列表攒到 4 万条时
        # 点一次表头要卡 2～5 秒，每完成一个任务还要整表重排一次、卡近 2 秒。
        # list.sort(key = ...) 每条只取一次键、比较全在 C 层，同样 4 万条只需 6～30 毫秒；
        # 新任务按二分查找插到该在的位置，不必重排
        self._sort_key_func = None
        self._sort_reverse = False

        self._rebuild_row_index()

    def _get_task_id(self, task_info: TaskInfo):
        return task_info.Basic.task_id

    def _rebuild_row_index(self):
        self._row_by_task_id = {
            task_info.Basic.task_id: row
            for row, task_info in enumerate(self._task_list)
        }

    def rowCount(self, parent = QModelIndex()):
        return len(self._task_list)
    
    def data(self, index: QModelIndex, role = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return
        
        task_info = self._task_list[index.row()]
        
        match role:
            case Qt.ItemDataRole.DisplayRole:
                return task_info.Basic.task_id
            
            case Qt.ItemDataRole.UserRole:
                return task_info
    
    def getRow(self, task_info: TaskInfo):
        return self._row_by_task_id.get(self._get_task_id(task_info), -1)

    def appendRow(self, task_info: TaskInfo):
        self.appendRows([task_info])

    def appendRows(self, task_info_list: List[TaskInfo]):
        if not task_info_list:
            return

        if self._sort_key_func is None:
            self._extendRows(task_info_list)

            return

        if not self._task_list:
            # 启动时整批载入：先把这一批排好，一次插入即可，用不着事后重排
            self._extendRows(sorted(task_info_list, key = self._sort_key_func, reverse = self._sort_reverse))

        elif len(task_info_list) <= self._INSERT_THRESHOLD:
            for task_info in task_info_list:
                row = self._insertPosition(task_info)

                self.beginInsertRows(QModelIndex(), row, row)

                self._task_list.insert(row, task_info)

                self.endInsertRows()

            # 插在中间会让后面的行号整体后移，插完统一重建一次
            self._rebuild_row_index()

        else:
            self._extendRows(task_info_list)

            self.resort()

    def _extendRows(self, task_info_list: List[TaskInfo]):
        start = self.rowCount()

        self.beginInsertRows(QModelIndex(), start, start + len(task_info_list) - 1)

        self._task_list.extend(task_info_list)

        self.endInsertRows()

        # 接在末尾不影响已有行号，只需补上新增的这一段
        for row, task_info in enumerate(task_info_list, start):
            self._row_by_task_id[task_info.Basic.task_id] = row

    def _insertPosition(self, task_info: TaskInfo):
        # 二分查找插入位置，落在键值相等的行之后，与稳定排序的结果一致
        key_func = self._sort_key_func
        key = key_func(task_info)

        low, high = 0, len(self._task_list)

        while low < high:
            mid = (low + high) // 2
            mid_key = key_func(self._task_list[mid])

            if (mid_key >= key) if self._sort_reverse else (mid_key <= key):
                low = mid + 1
            else:
                high = mid

        return low

    def setSortOrder(self, key: str, ascending: bool = True):
        self._sort_key_func = SORT_KEY_FUNCS.get(key)
        self._sort_reverse = not ascending

        self.resort()

    def resort(self):
        """
        按当前排序方式重排整个列表

        进度、文件大小这类排序键在下载过程中会变，由代理模型去抖后调这里。
        顺序没变时什么也不发：layoutChanged 会让代理模型重建映射、筛选生效时还要把每一行重新过滤一遍
        """
        if self._sort_key_func is None or len(self._task_list) < 2:
            return

        sorted_list = sorted(self._task_list, key = self._sort_key_func, reverse = self._sort_reverse)

        if all(new is old for new, old in zip(sorted_list, self._task_list)):
            return

        # PySide6 只暴露了这两个信号的无参重载，排序提示（VerticalSortHint）传不进去，只影响优化不影响正确性
        self.layoutAboutToBeChanged.emit()

        # 选中项、当前项都挂在持久索引上，重排后要按任务把它们挪到新行，否则选中会落到别的任务上
        old_indexes = self.persistentIndexList()
        old_tasks = [self._task_list[index.row()] for index in old_indexes]

        self._task_list[:] = sorted_list

        self._rebuild_row_index()

        self.changePersistentIndexList(old_indexes, [self.index(self.getRow(task_info)) for task_info in old_tasks])

        self.layoutChanged.emit()

    def updateRows(self, start_row: int, end_row: int):
        for row in range(start_row, end_row + 1):
            if not self.isRowInVisibleArea(row):
                continue

            index = self.index(row)

            self.dataChanged.emit(index, index)

    def removeRow(self, row, parent = QModelIndex()):
        if 0 <= row < self.rowCount():
            self.beginRemoveRows(parent, row, row)

            del self._task_list[row]

            self.endRemoveRows()

            self._rebuild_row_index()

            return True

        return False

    def removeTasks(self, task_info_list: List[TaskInfo]):
        # 批量移除。逐行调用 removeRow 时每次都要重建行索引，整体为 O(n²)，
        # 此处一次性过滤并重建，整体为 O(n)。
        task_id_set = {self._get_task_id(task_info) for task_info in task_info_list}

        if not task_id_set:
            return

        self.beginResetModel()

        self._task_list[:] = [
            task_info for task_info in self._task_list
            if self._get_task_id(task_info) not in task_id_set
        ]

        self.endResetModel()

        self._rebuild_row_index()

    def togglePauseResume(self, task_info: TaskInfo):
        # 在暂停与继续之间切换

        # 在此处实现懒加载，get不存在时会自动创建 Downloader 实例并加入管理器
        downloader = downloader_manager.get(task_info, create_if_not_exists = True) 

        match task_info.Download.status:
            case DownloadStatus.QUEUED:
                # 启动下载
                downloader.start()

            case DownloadStatus.DOWNLOADING:
                # 暂停下载
                downloader.pause()

                self.manageConcurrentDownloads()

            case DownloadStatus.PAUSED:
                # 继续下载
                downloader.resume()

            case DownloadStatus.FFMPEG_QUEUED:
                # 启动合并
                downloader.start_merge()

            case DownloadStatus.FAILED | DownloadStatus.FFMPEG_FAILED:
                # 重试下载
                downloader.retry()

        self.onUpdateData(task_info)

    def cancelDownload(self, task_info: TaskInfo):
        match task_info.Download.status:
            case DownloadStatus.COMPLETED:
                # 数据库删除交由写线程处理，界面立即移除该行
                task_manager.delete(task_info, completed = True)

                self.removeRow(self.getRow(task_info))

            case DownloadStatus.DOWNLOADING:
                downloader_manager.wait(task_info, lambda: task_manager.cancel_async(task_info))

            case DownloadStatus.MERGING | DownloadStatus.CONVERTING:
                # 合并和转换中的任务不允许取消
                return

            case _:
                task_manager.cancel_async(task_info)

    def batchStart(self, task_list: List[TaskInfo] = None):
        # task_list 为 None 时作用于整个列表；列表筛选生效时由代理模型传入当前可见的任务
        for task in self._targetTasks(task_list):
            if task.Download.status in [DownloadStatus.PAUSED, DownloadStatus.FFMPEG_FAILED, DownloadStatus.FAILED]:
                # 从暂停状态变为等待状态，由 manage_concurrent_downloads 统一调度
                task.Download.status = DownloadStatus.QUEUED

                self.onUpdateData(task)

        self.manageConcurrentDownloads()

    def batchPause(self, task_list: List[TaskInfo] = None):
        for task in self._targetTasks(task_list):
            if task.Download.status in [DownloadStatus.DOWNLOADING, DownloadStatus.QUEUED]:
                task.Download.status = DownloadStatus.PAUSED
                downloader = downloader_manager.get(task, create_if_not_exists = False)

                if downloader:
                    downloader.pause()

                self.onUpdateData(task)

    def batch_cancel(self, task_list: List[TaskInfo] = None):
        # 已完成的任务走批量路径：一次数据库删除 + 一次界面刷新。
        # 逐条处理时每条都要独立提交事务并重建行索引，任务较多时会长时间卡住界面。
        completed_tasks = []
        remaining_tasks = []

        for task in list(self._targetTasks(task_list)):
            match task.Download.status:
                case DownloadStatus.MERGING | DownloadStatus.CONVERTING:
                    # 只有非合并中的任务才允许取消
                    continue

                case DownloadStatus.COMPLETED:
                    completed_tasks.append(task)

                case _:
                    remaining_tasks.append(task)

        if completed_tasks:
            task_manager.delete_many(completed_tasks, completed = True)

            self.removeTasks(completed_tasks)

        for task in remaining_tasks:
            self.cancelDownload(task)

    def _targetTasks(self, task_list: List[TaskInfo] = None):
        return self._task_list if task_list is None else task_list

    def manageConcurrentDownloads(self):
        # 启动任务时可能同步走完整个流程并反过来再次触发调度。
        # 单次扫描的实现依赖本地计数，需要屏蔽重入，避免超出并发上限。
        # 被跳过的那次调度由 auto_manage_concurrent_downloads 信号在事件循环中补上。
        if self._managing_concurrent:
            return

        self._managing_concurrent = True

        try:
            self._manageConcurrentDownloads()

        finally:
            self._managing_concurrent = False

    def _manageConcurrentDownloads(self):
        # 自动调度同时下载的任务数量。
        # 原实现每启动一个任务就重新扫描一遍列表，整体为 O(n²)，此处改为单次扫描后按需启动。
        limit = config.get(config.download_parallel)

        active_count = 0
        queued_tasks = []

        for item in self._task_list:
            match item.Download.status:
                case DownloadStatus.DOWNLOADING | DownloadStatus.PARSING:
                    active_count += 1

                case DownloadStatus.QUEUED:
                    queued_tasks.append(item)

        for task in queued_tasks:
            if active_count >= limit:
                break

            self.togglePauseResume(task)

            # 启动后任务可能直接跳到合并阶段，此时不占用下载并发额度
            if task.Download.status in [DownloadStatus.DOWNLOADING, DownloadStatus.PARSING]:
                active_count += 1

        self.manageConcurrentMerges()

    def manageConcurrentMerges(self):
        # 与下载调度同理，屏蔽重入
        if self._managing_merges:
            return

        self._managing_merges = True

        try:
            self._manageConcurrentMerges()

        finally:
            self._managing_merges = False

    def _manageConcurrentMerges(self):
        # 自动调度同时合并的任务数量
        # 为避免多个合并任务同时进行导致高频资源占用，每次只允许一个合并任务进行，其他等待合并的任务都处于等待合并状态，由 manage_concurrent_merges 统一调度

        merging_count = 0
        merge_queued_tasks = []

        for item in self._task_list:
            match item.Download.status:
                case DownloadStatus.MERGING | DownloadStatus.CONVERTING:
                    merging_count += 1

                case DownloadStatus.FFMPEG_QUEUED:
                    merge_queued_tasks.append(item)

        for task in merge_queued_tasks:
            if merging_count >= 1:
                break

            self.togglePauseResume(task)

            # 无需调用 ffmpeg 的任务会同步完成，不占用合并额度
            if task.Download.status in [DownloadStatus.MERGING, DownloadStatus.CONVERTING]:
                merging_count += 1

    def connectUpdateDataSignal(self):
        signal_bus.download.update_downloading_item.connect(self.onUpdateData)

    def onUpdateData(self, task_info: TaskInfo):
        row = self.getRow(task_info)

        if row == -1:
            return

        if self.isRowInVisibleArea(row):

            model_index = self.index(row)

            self.dataChanged.emit(model_index, model_index)

    def isRowInVisibleArea(self, row: int):
        # 判断指定行是否在可见区域内
        view: QAbstractItemView = self.parent()

        if view and view.isVisible():
            viewport = view.viewport()
            item_rect = view.visualRect(self.index(row))

            return viewport.rect().intersects(item_rect)

        return False

    def redownload(self, task_info: TaskInfo):
        # 重新下载任务

        downloader = downloader_manager.get(task_info, create_if_not_exists = False)

  
        if task_info.Download.status == DownloadStatus.COMPLETED:
            # 已完成的任务需要从完成的列表中移动到正在下载的列表
            task_manager.reset(task_info)

            signal_bus.download.remove_from_completed_list.emit(task_info)

            task_manager.recreate(task_info)

            return

        elif task_info.Download.status == DownloadStatus.DOWNLOADING:
            downloader.pause()

        elif task_info.Download.status in [DownloadStatus.MERGING, DownloadStatus.CONVERTING]:
            # 合并和转换中的任务不允许重新下载
            return

        task_manager.reset(task_info)
        self.onUpdateData(task_info)

        self.manageConcurrentDownloads()
