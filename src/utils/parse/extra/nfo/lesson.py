import os

from utils.common.model.task_info import DownloadTaskInfo

from utils.module.pic.cover import Cover, CoverType

from utils.parse.extra.parser import Parser
from utils.parse.cheese import CheeseParser
from utils.parse.extra.file.metadata.lesson import TVShowMetaDataParser, EpisodeMetaDataParser
from utils.parse.extra.file.metadata.utils import Utils

class LessonNFOParser(Parser):
    def __init__(self, task_info: DownloadTaskInfo):
        Parser.__init__(self)

        self.task_info = task_info

    def download_tvshow_nfo(self):
        file_path = Utils.get_root_path(self.task_info, root = True)
        file_name = "tvshow.nfo"

        if self.check_file(file_path, file_name):
            return

        self.get_lesson_season_info()
        self.get_lesson_poster(file_path, "poster.jpg")

        file = TVShowMetaDataParser(self.task_info)
        contents = file.get_nfo_contents()

        self.save_file_ex(file_path, file_name, contents, "w")

    def download_episode_nfo(self):
        file = EpisodeMetaDataParser(self.task_info)
        contents = file.get_nfo_contents()

        self.save_file(f"{self.task_info.file_name}.nfo", contents, "w")

    def check_file(self, file_path: str, file_name: str):
        return os.path.exists(os.path.join(file_path, file_name))
    
    def get_lesson_season_info(self):
        self.season_info = CheeseParser.get_cheese_season_info(self.task_info.season_id)

        self.task_info.description = self.season_info.get("description")
        self.task_info.poster_url = self.season_info.get("poster_url")
        self.task_info.bangumi_pubdate = self.season_info.get("pubdate")

    def get_lesson_poster(self, file_path: str, file_name: str):
        contents = Cover.download_cover(self.task_info.poster_url, CoverType.JPG)

        self.save_file_ex(file_path, file_name, contents, "wb")
