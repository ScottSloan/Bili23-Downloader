from util.download.downloader.downloader import Downloader
from util.download.task.info import TaskInfo

class DownloaderManager:
    def __init__(self):
        # task_id 与 Downloader 绑定
        self.downloaders: dict[str, Downloader] = {}

    def add_downloader(self, task_info: TaskInfo):
        downloader = Downloader(task_info)

        self.downloaders[task_info.Basic.task_id] = downloader

    def add_downloader_list(self, task_info_list: list[TaskInfo]):
        for task_info in task_info_list:
            self.add_downloader(task_info)

    def get_downloader(self, task_id: str):
        return self.downloaders.get(task_id)

    def remove_downloader(self, task_id: str):
        if task_id in self.downloaders:
            self.downloaders[task_id].on_delete()
            
            del self.downloaders[task_id]

    def wait(self, task_id: str, on_end):
        downloader = self.get_downloader(task_id)
        
        if downloader:
            downloader.wait(on_end)

downloader_manager = DownloaderManager()
