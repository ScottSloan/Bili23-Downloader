import os

from utils.config import Config
from utils.common.model.task_info import DownloadTaskInfo
from utils.common.enums import CoverType

from utils.module.pic.cover import Cover

from utils.parse.extra.parser import Parser
from utils.parse.bangumi import BangumiParser
from utils.parse.extra.file.metadata.episode import TVShowMetaDataParser, SeasonMetadataParser, EpisodeMetadataParser
from utils.parse.extra.file.metadata.utils import Utils

class EpisodeNFOParser(Parser):
    def __init__(self, task_info: DownloadTaskInfo):
        Parser.__init__(self)

        self.task_info = task_info

    def download_tvshow_nfo(self):
        file_path = Utils.get_root_path(self.task_info)
        file_name = "tvshow.nfo"

        if self.check_file(file_path, file_name):
            return

        self.get_bangumi_season_info()
        self.get_bangumi_poster(file_path, "poster.jpg")

        file = TVShowMetaDataParser(self.task_info)
        contents = file.get_nfo_contents()

        self.save_file_ex(file_path, file_name, contents, "w")

    def download_season_nfo(self):
        file_path = self.task_info.download_path
        file_name = "season.nfo"

        if self.check_file(file_path, file_name):
            return

        self.get_bangumi_season_info()

        if Config.Download.strict_naming:
            file_name = f"season{self.task_info.season_num:02}-poster.jpg"
        else:
            file_name = "poster.jpg"

        self.get_bangumi_poster(Utils.get_root_path(self.task_info), file_name)

        file = SeasonMetadataParser(self.task_info)
        contents = file.get_nfo_contents()

        self.save_file_ex(file_path, file_name, contents, "w")

    def download_episode_nfo(self):
        file = EpisodeMetadataParser(self.task_info)
        contents = file.get_nfo_contents()

        self.save_file(f"{self.task_info.file_name}.nfo", contents, "w")

    def check_file(self, file_path: str, file_name: str):
        return os.path.exists(os.path.join(file_path, file_name))
        
    def get_bangumi_season_info(self):
        if not hasattr(self, "season_info"):
            self.season_info = BangumiParser.get_bangumi_season_info(self.task_info.season_id)

        self.task_info.poster_url = self.season_info.get("poster_url")
        self.task_info.description = self.season_info.get("description")
        self.task_info.actors = self.season_info.get("actors")
        self.task_info.bangumi_tags = self.season_info.get("tags")
        self.task_info.bangumi_pubdate = self.season_info.get("pubdate")
        self.task_info.seasons = self.season_info.get("seasons")
        self.task_info.rating = self.season_info.get("rating")
        self.task_info.rating_count = self.season_info.get("rating_count")
        self.task_info.areas = self.season_info.get("areas")

    def get_bangumi_poster(self, file_path: str, file_name: str):
        contents = Cover.download_cover(self.task_info.poster_url, CoverType.JPG)

        self.save_file_ex(file_path, file_name, contents, "wb")
