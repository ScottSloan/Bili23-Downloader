from utils.common.model.task_info import DownloadTaskInfo

class EpisodeNFOParser:
    def __init__(self, task_info: DownloadTaskInfo):
        self.task_info = task_info

    def download_tvshow_nfo(self):
        pass

    def download_season_nfo(self):
        pass

    def download_episode_nfo(self):
        if self.task_info.section_title == "正片":
            pass
        else:
            pass

