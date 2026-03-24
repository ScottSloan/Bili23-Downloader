from util.network.request import NetworkRequestWorker, ResponseType
from util.parse.additional.file.metadata_nfo import MetadataNFO
from util.parse.additional.base import AdditionalParserBase
from util.download.task.info import TaskInfo
from util.common.enum import MetadataType
from util.common.config import config
from util.thread import SyncTask

from pathlib import Path

class MetadataParser(AdditionalParserBase):
    def __init__(self, task_info: TaskInfo):
        super().__init__(task_info)

    def parse(self):
        match config.get(config.metadata_type):
            case MetadataType.NFO:
                contents_list = MetadataNFO(self.task_info).generate()

                for entry in contents_list:
                    contents, name, qualifier = entry["contents"], entry["name"], entry["qualifier"]

                    # 去除 contents 中多余空行
                    contents = "\n".join([line for line in contents.splitlines() if line.strip() != ""])

                    self._write(contents, suffix = "nfo", name = name, qualifier = qualifier)

                self._save_poster()

            case MetadataType.JSON:
                pass

    def _save_poster(self):
        def on_success(response: bytes):
            self._write(response, suffix = "jpg", name = "poster")

        path = Path(self.task_info.File.download_path, self.task_info.File.folder, "poster.jpg")

        if not path.exists() and self.task_info.Episode.poster:
            worker = NetworkRequestWorker(self.task_info.Episode.poster, response_type = ResponseType.BYTES)
            worker.success.connect(on_success)
            worker.error.connect(self._on_error)

            SyncTask.run(worker)
