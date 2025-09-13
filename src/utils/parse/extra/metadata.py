from utils.common.model.task_info import DownloadTaskInfo
from utils.common.enums import MetadataType

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

            case MetadataType.JSON:
                self.task_info.output_type = "json"
                self.generate_json()

    def generate_nfo(self):
        file = MetadataNFOFile(self.task_info)
        contents = file.get_contents()

        self.save_file(f"{self.task_info.file_name}.nfo", contents, "w")

    def generate_json(self):
        pass