from util.common.enum import ToastNotificationCategory
from util.common import signal_bus, Translator

from ..task.info import TaskInfo

from .downloader import Downloader

class DownloaderManager:
    def __init__(self):
        # task_id 与 Downloader 绑定
        self.downloaders: dict[str, Downloader] = {}

    def add(self, task_info: TaskInfo):
        downloader = Downloader(task_info)

        self.downloaders[task_info.Basic.task_id] = downloader

    def add_list(self, task_info_list: list[TaskInfo]):
        for task_info in task_info_list:
            self.add(task_info)

    def get(self, task_info: TaskInfo, create_if_not_exists = True):
        task_id = task_info.Basic.task_id

        if task_id in self.downloaders:
            return self.downloaders[task_id]
        
        else:
            if create_if_not_exists:
                self.add(task_info)

                return self.downloaders[task_id]

        return None
    
    def check(self, task_id: str):
        if task_id in self.downloaders:
            return True
        
        return False

    def remove(self, task_id: str):
        if task_id in self.downloaders:
            self.downloaders[task_id].on_delete()
            
            self.downloaders.pop(task_id)

    def wait(self, task_info: TaskInfo, callback):
        downloader = self.get(task_info)
        
        if downloader:
            downloader.wait(callback)

    def show_notification(self):
        # 如果没有正在下载的任务了，发射下载完成的通知信号

        if len(self.downloaders) == 0:
            signal_bus.toast.sys_show.emit(
                ToastNotificationCategory.INFO,
                Translator.TIP_MESSAGES("DOWNLOAD_COMPLETED"),
                Translator.TIP_MESSAGES("DOWNLOAD_COMPLETED_DETAIL")
            )

downloader_manager = DownloaderManager()
