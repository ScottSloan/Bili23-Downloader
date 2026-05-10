from PySide6.QtCore import QModelIndex, Qt, QSize, QTimer, Signal
from PySide6.QtWidgets import QAbstractItemView

from gui.component.view_model.model_base import CoverQueryModelBase

from util.download.downloader.manager import downloader_manager
from util.download.task.manager import task_manager
from util.download.task.info import TaskInfo
from util.download.scheduler.resource_allocator import resource_allocator
from util.common.enum import DownloadStatus
from util.common import signal_bus, config

from typing import List, Dict
import logging

logger = logging.getLogger(__name__)

class DownloadListModel(CoverQueryModelBase):
    _progress_signal = Signal(object, object)

    def __init__(self, task_list: list, parent = None):
        super().__init__(parent)

        self._cover_size = QSize(144, 80)
        self._task_list: List[TaskInfo] = task_list

        self._pending_updates: Dict[str, TaskInfo] = {}

        self._progress_timer = QTimer(self)
        self._progress_timer.setInterval(80)
        self._progress_timer.timeout.connect(self._flush_pending_updates)
        self._progress_timer.start()

        self._fragment_progress: Dict[str, Dict[str, dict]] = {}
        self._max_progress: Dict[str, float] = {}

        self._progress_signal.connect(self._on_progress_signal)

    def rowCount(self, parent = QModelIndex()):
        return len(self._task_list)
    
    def data(self, index: QModelIndex, role = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return
        
        task_info = self._task_list[index.row()]
        
        match role:
            case Qt.ItemDataRole.DisplayRole:
                return task_info["task_id"]
            
            case Qt.ItemDataRole.UserRole:
                return task_info
    
    def getRow(self, task_info: TaskInfo):
        task_id = task_info.Basic.task_id
        for i, task in enumerate(self._task_list):
            if task.Basic.task_id == task_id:
                return i
        return -1

    def appendRow(self, task_info: TaskInfo):
        row = self.rowCount()

        self.beginInsertRows(QModelIndex(), row, row)

        self._task_list.append(task_info)

        self.endInsertRows()

    def appendRows(self, task_info_list: List[TaskInfo]):
        row = self.rowCount()

        self.beginInsertRows(QModelIndex(), row, row + len(task_info_list) - 1)

        self._task_list.extend(task_info_list)

        self.endInsertRows()

    def updateRows(self, start_row: int, end_row: int):
        for row in range(start_row, end_row + 1):
            index = self.index(row)

            self.dataChanged.emit(index, index)

    def removeRow(self, row, parent = QModelIndex()):
        if 0 <= row < self.rowCount():
            self.beginRemoveRows(parent, row, row)

            del self._task_list[row]

            self.endRemoveRows()

            return True
        
        return False

    def togglePauseResume(self, task_info: TaskInfo):
        # 在暂停与继续之间切换

        # 在此处实现懒加载，get不存在时会自动创建 Downloader 实例并加入管理器
        import logging
        logger = logging.getLogger(__name__)
        logger.info(f"togglePauseResume - task_info.cookie_file: {task_info.cookie_file}")
        
        downloader = downloader_manager.get(task_info, create_if_not_exists = True) 

        match task_info.Download.status:
            case DownloadStatus.QUEUED:
                # 启动下载 - 设置回调以更新 UI
                downloader.set_callbacks(
                    progress=lambda data: self._on_download_progress(task_info, data),
                    finish=lambda url: self._on_download_finish(task_info),
                    error=lambda msg: self._on_download_error(task_info, msg)
                )
                active_tasks = [t for t in self._task_list if t.Download.status == DownloadStatus.DOWNLOADING]
                thread_count = resource_allocator.calculate_thread_allocation(task_info, active_tasks)
                downloader.set_thread_count(thread_count)
                resource_allocator.register_queue(task_info)
                downloader.start()

            case DownloadStatus.DOWNLOADING:
                # 暂停下载
                downloader.pause()

                self.manageConcurrentDownloads()

            case DownloadStatus.PAUSED:
                # 继续下载
                resource_allocator.register_queue(task_info)
                downloader.resume()

            case DownloadStatus.FFMPEG_QUEUED:
                # 启动合并
                downloader.start_merge()

            case DownloadStatus.FAILED | DownloadStatus.FFMPEG_FAILED:
                # 重试下载
                downloader.set_callbacks(
                    progress=lambda data: self._on_download_progress(task_info, data),
                    finish=lambda url: self._on_download_finish(task_info),
                    error=lambda msg: self._on_download_error(task_info, msg)
                )
                active_tasks = [t for t in self._task_list if t.Download.status == DownloadStatus.DOWNLOADING]
                thread_count = resource_allocator.calculate_thread_allocation(task_info, active_tasks)
                downloader.set_thread_count(thread_count)
                resource_allocator.register_queue(task_info)
                downloader.retry()

        self.onUpdateData(task_info)

    def _on_download_progress(self, task_info: TaskInfo, data: dict):
        self._progress_signal.emit(task_info, data)

    def _on_progress_signal(self, task_info: TaskInfo, data: dict):
        task_id = task_info.Basic.task_id

        if data.get("status") == "merging":
            progress = data.get("progress", 0)
            info = data.get("info", "")

            task_info.Download.progress = progress
            task_info.Download.info_label = info

            self._pending_updates[task_id] = task_info
            return

        if data.get("status") == "finished":
            filename = data.get("filename", "")
            if filename and task_id in self._fragment_progress:
                fragments = self._fragment_progress[task_id]
                if filename in fragments:
                    fragments[filename]["downloaded"] = fragments[filename]["total"]
            return

        if data.get("status") != "downloading":
            return

        filename = data.get("filename", "")
        downloaded_bytes = data.get("downloaded_bytes", 0) or 0
        total_bytes = data.get("total_bytes", 0) or data.get("total_bytes_estimate", 0) or 0

        if task_id not in self._fragment_progress:
            self._fragment_progress[task_id] = {}

        fragments = self._fragment_progress[task_id]

        if filename and filename not in fragments:
            for fname, fdata in fragments.items():
                if not fdata.get("completed"):
                    fdata["completed"] = True

        if filename and total_bytes > 0:
            if filename not in fragments:
                fragments[filename] = {"downloaded": 0, "total": total_bytes}
            prev_downloaded = fragments[filename]["downloaded"]
            if downloaded_bytes > prev_downloaded:
                fragments[filename]["downloaded"] = downloaded_bytes
            fragments[filename]["total"] = total_bytes

        percent = self._calc_overall_progress(task_id, data)
        speed = data.get("speed", 0) or 0

        resource_allocator.record_speed(task_id, speed)

        total_downloaded = sum(f["downloaded"] for f in fragments.values())
        total_all = sum(f["total"] for f in fragments.values())

        task_info.Download.progress = percent
        task_info.Download.speed = speed
        task_info.Download.downloaded_size = total_downloaded
        task_info.Download.total_size = total_all if total_all > 0 else total_bytes

        speed_str = data.get("speed_str", "")
        eta = data.get("eta", "")
        if speed_str or eta:
            task_info.Download.info_label = f"{speed_str} - {eta}" if speed_str and eta else (speed_str or eta)

        self._pending_updates[task_info.Basic.task_id] = task_info

    def _calc_overall_progress(self, task_id: str, data: dict) -> float:
        fragments = self._fragment_progress.get(task_id, {})

        if fragments:
            completed_bytes = sum(f["total"] for f in fragments.values() if f.get("completed"))
            active_downloaded = sum(f["downloaded"] for f in fragments.values() if not f.get("completed"))
            active_total = sum(f["total"] for f in fragments.values() if not f.get("completed"))

            total_downloaded = completed_bytes + active_downloaded
            total_all = completed_bytes + active_total

            if total_all > 0:
                raw = (total_downloaded / total_all) * 100
                active_count = sum(1 for f in fragments.values() if not f.get("completed"))
                if completed_bytes == 0 and active_count == 1:
                    raw = min(raw, 99.0)
                raw = min(raw, 100.0)
            else:
                raw = 0.0
        else:
            downloaded = data.get("downloaded_bytes", 0) or 0
            total = data.get("total_bytes", 0) or data.get("total_bytes_estimate", 0) or 0
            if total > 0:
                raw = min((downloaded / total) * 100, 99.0)
            else:
                fragment_index = data.get("fragment_index", 0)
                fragment_count = data.get("fragment_count", 0)
                if fragment_count > 0:
                    raw = min((fragment_index / fragment_count) * 100, 99.0)
                else:
                    raw = 0.0

        last_max = self._max_progress.get(task_id, 0.0)
        if raw > last_max:
            self._max_progress[task_id] = raw

        return max(raw, last_max)

    def _flush_pending_updates(self):
        if self._pending_updates:
            for task_id, task_info in self._pending_updates.items():
                self._emit_update(task_info)
            self._pending_updates.clear()
        else:
            self._refresh_visible_downloads()

    def _refresh_visible_downloads(self):
        view: QAbstractItemView = self.parent()
        if not view:
            return
        viewport = view.viewport()
        if not viewport:
            return
        visible_rect = viewport.rect()
        for row in range(self.rowCount()):
            task_info = self._task_list[row]
            if task_info.Download.status == DownloadStatus.DOWNLOADING:
                item_rect = view.visualRect(self.index(row))
                if item_rect.isValid() and visible_rect.intersects(item_rect):
                    model_index = self.index(row)
                    self.dataChanged.emit(model_index, model_index)

    def _emit_update(self, task_info: TaskInfo):
        row = self.getRow(task_info)
        if row != -1:
            model_index = self.index(row)
            self.dataChanged.emit(model_index, model_index)

    def _on_download_finish(self, task_info: TaskInfo):
        if task_info.Download.status == DownloadStatus.FFMPEG_QUEUED:
            self._fragment_progress.pop(task_info.Basic.task_id, None)
            self._max_progress.pop(task_info.Basic.task_id, None)
            resource_allocator.unregister(task_info.Basic.task_id)

            self._emit_update(task_info)

            self.manageConcurrentMerges()
            return

        task_info.Download.status = DownloadStatus.COMPLETED
        task_info.Download.progress = 100.0

        self._fragment_progress.pop(task_info.Basic.task_id, None)
        self._max_progress.pop(task_info.Basic.task_id, None)
        resource_allocator.unregister(task_info.Basic.task_id)

        self._emit_update(task_info)

        signal_bus.download.remove_from_downloading_list.emit(task_info)
        signal_bus.download.add_to_completed_list.emit([task_info])

        task_manager.mark_as_completed(task_info)

        self.manageConcurrentDownloads()

    def _on_download_error(self, task_info: TaskInfo, error_msg: str):
        task_info.Download.status = DownloadStatus.FAILED
        task_info.Download.info_label = f"错误: {error_msg}"

        self._fragment_progress.pop(task_info.Basic.task_id, None)
        self._max_progress.pop(task_info.Basic.task_id, None)
        resource_allocator.unregister(task_info.Basic.task_id)

        self._emit_update(task_info)
        
        self.manageConcurrentDownloads()

    def cancelDownload(self, task_info: TaskInfo):
        import logging
        logger = logging.getLogger(__name__)
        
        match task_info.Download.status:
            case DownloadStatus.COMPLETED:
                logger.info(f"删除已完成任务: {task_info.Basic.task_id}, title={task_info.Basic.show_title}")
                task_manager.delete_completed(task_info)
                self.removeRow(self.getRow(task_info))
                logger.info(f"已从 UI 移除任务")

            case DownloadStatus.DOWNLOADING | DownloadStatus.MERGING | DownloadStatus.CONVERTING:
                downloader_manager.wait(task_info, lambda: self._cancelAndRemove(task_info))

            case _:
                self._cancelAndRemove(task_info)

        # 更新下载数量徽章
        signal_bus.download.update_downloading_count.emit(self.rowCount())

    def _cancelAndRemove(self, task_info: TaskInfo):
        task_manager.cancel(task_info)
        self._fragment_progress.pop(task_info.Basic.task_id, None)
        self._max_progress.pop(task_info.Basic.task_id, None)
        resource_allocator.unregister(task_info.Basic.task_id)
        row = self.getRow(task_info)
        if row != -1:
            self.removeRow(row)

    def batchStart(self):
        for task in self._task_list:
            if task.Download.status in [DownloadStatus.PAUSED, DownloadStatus.FFMPEG_FAILED, DownloadStatus.FAILED]:
                # 从暂停状态变为等待状态，由 manage_concurrent_downloads 统一调度
                task.Download.status = DownloadStatus.QUEUED

                self.onUpdateData(task)

        self.manageConcurrentDownloads()

    def batchPause(self):
        for task in self._task_list:
            if task.Download.status in [DownloadStatus.DOWNLOADING, DownloadStatus.QUEUED]:
                task.Download.status = DownloadStatus.PAUSED
                downloader = downloader_manager.get(task, create_if_not_exists = False)

                if downloader:
                    downloader.pause()

                self.onUpdateData(task)

    def batch_cancel(self):
        self.beginResetModel()

        for task in list(self._task_list):
            if task.Download.status not in [DownloadStatus.MERGING, DownloadStatus.CONVERTING]:
                # 只有非合并中的任务才允许取消
                self.cancelDownload(task)

        self.endResetModel()
        
        # 确保所有任务都被移除
        self._task_list.clear()
        self._fragment_progress.clear()
        self._max_progress.clear()
        resource_allocator._queue_times.clear()
        resource_allocator._speed_history.clear()
        
        # 更新下载数量徽章
        signal_bus.download.update_downloading_count.emit(0)

    def manageConcurrentDownloads(self):
        active = [item for item in self._task_list if item.Download.status in [DownloadStatus.DOWNLOADING, DownloadStatus.PARSING]]
        queued = [item for item in self._task_list if item.Download.status == DownloadStatus.QUEUED]

        if not queued:
            self.manageConcurrentMerges()
            return

        base_limit = config.get(config.download_parallel)
        effective_limit = resource_allocator.adjust_parallel_limit(active, base_limit)

        while len(active) < effective_limit and queued:
            next_task = resource_allocator.select_next_task(queued, active)
            if next_task is None:
                break
            queued.remove(next_task)
            self.togglePauseResume(next_task)
            active = [item for item in self._task_list if item.Download.status in [DownloadStatus.DOWNLOADING, DownloadStatus.PARSING]]

        self.manageConcurrentMerges()

    def manageConcurrentMerges(self):
        # 自动调度同时合并的任务数量
        # 为避免多个合并任务同时进行导致高频资源占用，每次只允许一个合并任务进行，其他等待合并的任务都处于等待合并状态，由 manage_concurrent_merges 统一调度

        while True:
            merging = [item for item in self._task_list if item.Download.status in [DownloadStatus.MERGING, DownloadStatus.CONVERTING]]
            merge_queued = [item for item in self._task_list if item.Download.status == DownloadStatus.FFMPEG_QUEUED]

            if len(merging) >= 1 or not merge_queued:
                break

            next_task = merge_queued.pop(0)
            self.togglePauseResume(next_task)

    def connectUpdateDataSignal(self):
        signal_bus.download.update_downloading_item.connect(self.onUpdateData)

    def onUpdateData(self, task_info: TaskInfo):
        row = self.getRow(task_info)

        if row != -1:
            model_index = self.index(row)
            self.dataChanged.emit(model_index, model_index)

    def _refresh_downloading_progress(self):
        self._flush_pending_updates()
        for task_info in self._task_list:
            if task_info.Download.status == DownloadStatus.DOWNLOADING:
                row = self.getRow(task_info)
                if row != -1:
                    model_index = self.index(row)
                    self.dataChanged.emit(model_index, model_index)

    def isRowInVisibleArea(self, row: int):
        # 判断指定行是否在可见区域内
        view: QAbstractItemView = self.parent()

        if view:
            viewport = view.viewport()
            item_rect = view.visualRect(self.index(row))

            return viewport.rect().intersects(item_rect)

        return False

    def redownload(self, task_info: TaskInfo):
        # 重新下载任务

        downloader = downloader_manager.get(task_info, create_if_not_exists=False)

        if task_info.Download.status == DownloadStatus.COMPLETED:
            # 已完成的任务需要从完成的列表中移动到正在下载的列表
            task_manager.reset(task_info)

            signal_bus.download.remove_from_completed_list.emit(task_info)

            task_manager.recreate(task_info)

            return

        elif task_info.Download.status == DownloadStatus.DOWNLOADING:
            if downloader:
                downloader.pause()

        elif task_info.Download.status in [DownloadStatus.MERGING, DownloadStatus.CONVERTING]:
            # 合并和转换中的任务不允许重新下载
            return

        self._fragment_progress.pop(task_info.Basic.task_id, None)
        self._max_progress.pop(task_info.Basic.task_id, None)
        resource_allocator.unregister(task_info.Basic.task_id)
        task_manager.reset(task_info)
        self.onUpdateData(task_info)

        self.manageConcurrentDownloads()
