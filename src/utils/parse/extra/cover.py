from utils.config import Config
from utils.common.model.task_info import DownloadTaskInfo
from utils.common.enums import TemplateType

from utils.module.pic.cover import Cover

from utils.parse.extra.parser import Parser

class CoverParser(Parser):
    def __init__(self, task_info: DownloadTaskInfo):
        Parser.__init__(self)

        self.task_info = task_info

    def parse(self):
        self.generate_cover()

        self.task_info.total_file_size += self.total_file_size

    def generate_cover(self):
        cover_type = Cover.get_cover_type(Config.Basic.cover_file_type)
        self.task_info.output_type = cover_type.lstrip(".")

        contents = Cover.download_cover(self.task_info.cover_url)

        if self.task_info.extra_option.get("download_metadata_file") and TemplateType.Bangumi_strict.value and self.task_info.episode_tag:
            file_name = f"{self.task_info.episode_tag}{cover_type}"
        else:
            file_name = f"{self.task_info.file_name}{cover_type}"

        self.save_file(file_name, contents, "wb")