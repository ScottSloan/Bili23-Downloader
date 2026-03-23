from util.download.downloader.downloader import Downloader
from util.download.task.info import TaskInfo

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

    def wait(self, task_id: str, callback):
        downloader = self.get(task_id)
        
        if downloader:
            downloader.wait(callback)

downloader_manager = DownloaderManager()
