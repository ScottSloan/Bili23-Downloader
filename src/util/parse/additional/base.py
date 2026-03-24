from util.parse.parser.base import ParserBase
from util.download.task.info import TaskInfo

from pathlib import Path

class AdditionalParserBase(ParserBase):
    def __init__(self):
        super().__init__()

        self.task_info: TaskInfo = None

    def _write(self, contents: str, suffix: str, name: str = None, qualifier: str = None):
        if name is None:
            name = self.task_info.File.name

        if qualifier:
            name_parts = f"{name}.{qualifier}"
        else:
            name_parts = name

        path = self.__base_path / f"{name_parts}.{suffix}"

        with open(path, "w", encoding = "utf-8") as f:
            f.write(contents)
    
    @property
    def __base_path(self):
        return Path(self.task_info.File.download_path, self.task_info.File.folder)
