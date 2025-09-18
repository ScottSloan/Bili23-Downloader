import os

from utils.common.model.task_info import DownloadTaskInfo
from utils.common.enums import MetadataType, ParseType

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

        self.save_file(f"{self.task_info.file_name}.nfo", contents, "w")

    def generate_json(self):
        pass

    def generate_bangumi_season_nfo(self):
        if ParseType(self.task_info.parse_type) == ParseType.Bangumi:
            download_path = os.path.join(self.task_info.download_base_path, self.task_info.series_title_original)

            if os.path.exists(os.path.join(download_path, f"tvshow.nfo")):
                return

            self.get_bangumi_season_info()

            self.task_info.download_path = download_path

            file = MetadataNFOFile(self.task_info)
            contents = file.get_bangumi_season_contents()

            self.save_file(f"tvshow.nfo", contents, "w")

    def get_bangumi_season_info(self):
        from utils.parse.bangumi import BangumiParser

        season_info = BangumiParser.get_bangumi_season_info(self.task_info.media_id)

        self.task_info.poster_url = season_info.get("poster_url")
        self.task_info.description = season_info.get("description")
        self.task_info.actors = season_info.get("actors")
        self.task_info.bangumi_tags = season_info.get("tags")