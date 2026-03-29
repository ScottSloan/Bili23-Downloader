from util.network.request import NetworkRequestWorker, ResponseType
from util.parse.additional import AdditionalParserBase
from util.download.task.info import TaskInfo
from util.thread import SyncTask
from util.common import config

class CoverParser(AdditionalParserBase):
    def __init__(self, task_info: TaskInfo):
        super().__init__(task_info)

    def parse(self):
        suffix = config.get(config.cover_type).value
        contents = self._get_cover_contents(suffix)

        self._write(contents, suffix = suffix, name = self.task_info.File.name)

    def _get_cover_contents(self, suffix: str):
        def on_success(response: bytes):
            nonlocal contents

            contents = response
            
        contents = None
        
        url = "{url}@.{suffix}".format(url = self.task_info.Episode.cover, suffix = suffix)

        worker = NetworkRequestWorker(url, response_type = ResponseType.BYTES)
        worker.success.connect(on_success)
        worker.error.connect(self._on_error)

        SyncTask.run(worker)

        return contents
