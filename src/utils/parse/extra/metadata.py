from utils.config import Config
from utils.common.model.task_info import DownloadTaskInfo
from utils.common.enums import MetadataType, ParseType, TemplateType

from utils.parse.extra.parser import Parser
from utils.parse.extra.nfo.video import VideoNFOParser
from utils.parse.extra.nfo.movie import MovieNFOParser
from utils.parse.extra.nfo.episode import EpisodeNFOParser
from utils.parse.extra.nfo.lesson import LessonNFOParser

class MetadataParser(Parser):
    def __init__(self, task_info: DownloadTaskInfo):
        Parser.__init__(self)

        self.task_info = task_info

    def parse(self):
        match MetadataType(self.task_info.extra_option.get("metadata_file_type")):
            case MetadataType.NFO:
                self.task_info.output_type = "nfo"
                self.generate_nfo()

            case MetadataType.JSON:
                self.task_info.output_type = "json"
                self.generate_json()

        self.task_info.total_file_size += self.total_file_size

    def generate_nfo(self):
        match ParseType(self.task_info.parse_type):
            case ParseType.Video:
                self.generate_video_nfo()

            case ParseType.Bangumi:
                if self.task_info.bangumi_type == "电影":
                    self.generate_movie_nfo()
                else:
                    self.generate_episode_nfo()

            case ParseType.Cheese:
                self.generate_lesson_nfo()
    
    def generate_video_nfo(self):
        parser = VideoNFOParser(self.task_info)

        parser.download_video_nfo()

        self.total_file_size += parser.total_file_size

    def generate_movie_nfo(self):
        option = Config.Basic.scrape_option.get("movie")

        parser = MovieNFOParser(self.task_info)

        if option.get("download_movie_nfo"):
            # movie
            parser.download_movie_nfo()

        if option.get("download_episode_nfo"):
            # episode
            parser.download_episode_nfo()

        self.total_file_size += parser.total_file_size

    def generate_episode_nfo(self):
        option = Config.Basic.scrape_option.get("episode")

        parser = EpisodeNFOParser(self.task_info)

        if option.get("download_tvshow_nfo"):
            # tvshow
            parser.download_tvshow_nfo()

        if option.get("download_season_nfo"):
            # season
            parser.download_season_nfo()

        if option.get("download_episode_nfo"):
            # episode
            parser.download_episode_nfo()

        self.total_file_size += parser.total_file_size

    def generate_lesson_nfo(self):
        option = Config.Basic.scrape_option.get("lesson")

        parser = LessonNFOParser(self.task_info)

        if option.get("download_tvshow_nfo"):
            # tvshow
            parser.download_tvshow_nfo()

        if option.get("download_episode_nfo"):
            # episode
            parser.download_episode_nfo()

        self.total_file_size += parser.total_file_size

    def generate_json(self):
        pass
