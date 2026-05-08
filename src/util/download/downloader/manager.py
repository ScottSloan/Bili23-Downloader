from util.download.downloader.yt_dlp_downloader import YTDLPDownloader
from util.common.enum import ToastNotificationCategory
from util.common import signal_bus, Translator
from util.download.task.info import TaskInfo

import logging

logger = logging.getLogger(__name__)


class DownloaderManager:
    def __init__(self):
        self.downloaders: dict[str, YTDLPDownloader] = {}
        self.task_infos: dict[str, TaskInfo] = {}

    def add(self, task_info: TaskInfo):
        downloader = YTDLPDownloader()
        downloader.set_task_info(task_info)
        self.downloaders[task_info.Basic.task_id] = downloader
        self.task_infos[task_info.Basic.task_id] = task_info

    def add_list(self, task_info_list: list[TaskInfo]):
        for task_info in task_info_list:
            self.add(task_info)

    def get(self, task_info: TaskInfo, create_if_not_exists=True):
        task_id = task_info.Basic.task_id

        if task_id in self.downloaders:
            return self.downloaders[task_id]
        else:
            if create_if_not_exists:
                self.add(task_info)
                return self.downloaders[task_id]

        return None

    def get_task_info(self, task_info: TaskInfo):
        task_id = task_info.Basic.task_id
        return self.task_infos.get(task_id, task_info)

    def check(self, task_id: str):
        return task_id in self.downloaders

    def remove(self, task_id: str):
        if task_id in self.downloaders:
            downloader = self.downloaders[task_id]
            if downloader._is_downloading:
                downloader.pause()
            self.downloaders.pop(task_id)
        if task_id in self.task_infos:
            self.task_infos.pop(task_id)

    def wait(self, task_info: TaskInfo, callback):
        downloader = self.get(task_info, create_if_not_exists=False)
        if downloader:
            downloader.pause()
            callback()
        else:
            logger.warning(f"Downloader not found for task {task_info.Basic.task_id}")
            callback()

    def show_notification(self):
        if len(self.downloaders) == 0:
            signal_bus.toast.sys_show.emit(
                ToastNotificationCategory.INFO,
                Translator.TIP_MESSAGES("DOWNLOAD_COMPLETED"),
                Translator.TIP_MESSAGES("DOWNLOAD_COMPLETED_DETAIL")
            )


downloader_manager = DownloaderManager()
