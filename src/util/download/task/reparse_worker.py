from PySide6.QtCore import QRunnable, Signal, QObject

from util.parse.episode.tree import EpisodeData, Attribute
from util.common import signal_bus

class ReparseWorkerSignals(QObject):
    finished = Signal(list)

class ReparseWorker(QRunnable):
    def __init__(self, episode_info: dict):
        super().__init__()

        self.episode_info = episode_info
        self.signals = ReparseWorkerSignals()

    def run(self):
        episode_id = self.episode_info.get("episode_id", "")
        extra_data = EpisodeData.get_episode_data(episode_id)
        
        task_info = {
            **self.episode_info,
            **extra_data,
            **self.episode_info.get("related_titles", {}),
            **self.episode_info.get("uploader_info", {}),
        }
        
        signal_bus.download.create_task.emit([task_info], "")
