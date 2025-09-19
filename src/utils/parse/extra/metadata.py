import os

from utils.config import Config
from utils.common.model.task_info import DownloadTaskInfo
from utils.common.enums import MetadataType, ParseType, CoverType
from utils.parse.bangumi import BangumiParser
from utils.common.formatter.file_name_v2 import FileNameFormatter

from utils.module.pic.cover import Cover

from utils.parse.extra.parser import Parser
from utils.parse.extra.file.metadata_nfo import MetadataNFOFile

class MetadataParser(Parser):
    def __init__(self, task_info: DownloadTaskInfo):
        Parser.__init__(self)

        self.task_info = task_info

    def parse(self):
        match MetadataType(self.task_info.extra_option.get("metadata_file_type")):
            case MetadataType.NFO:
                self.task_info.output_type = "nfo"
                self.generate_nfo()

                self.generate_bangumi_season_nfo()

            case MetadataType.JSON:
                self.task_info.output_type = "json"
                self.generate_json()

    def generate_nfo(self):
        file = MetadataNFOFile(self.task_info)
        contents = file.get_contents()

        if self.task_info.episode_tag:
            file_name = f"{self.task_info.episode_tag}.nfo"
        else:
            file_name = f"{FileNameFormatter.get_legal_file_name(self.task_info.title)}.nfo"

        self.save_file(file_name, contents, "w")

    def generate_json(self):
        pass

    def generate_bangumi_season_nfo(self):
        if ParseType(self.task_info.parse_type) == ParseType.Bangumi and Config.Download.strict_naming:
            download_path = os.path.join(self.task_info.download_base_path, self.task_info.series_title_original)

            if os.path.exists(os.path.join(download_path, f"tvshow.nfo")):
                return

            self.get_bangumi_season_info()

            file = MetadataNFOFile(self.task_info)
            contents = file.get_bangumi_season_contents()

            self.save_file_ex(download_path, f"tvshow.nfo", contents, "w")

            self.save_bangumi_season_poster(download_path)

    def get_bangumi_season_info(self):
        season_info = BangumiParser.get_bangumi_season_info(self.task_info.media_id)

        self.task_info.poster_url = season_info.get("poster_url")
        self.task_info.description = season_info.get("description")
        self.task_info.actors = season_info.get("actors")
        self.task_info.bangumi_tags = season_info.get("tags")
        self.task_info.bangumi_pubdate = season_info.get("pubdate")

    def save_bangumi_season_poster(self, download_path: str = None):
        contents = Cover.download_cover(self.task_info.poster_url, CoverType.JPG)

        self.save_file_ex(download_path, f"poster.jpg", contents, "wb")
