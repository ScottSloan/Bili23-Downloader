from util.network.request import NetworkRequestWorker, ResponseType
from util.parse.additional.base import AdditionalParserBase
from util.download.task.info import TaskInfo
from util.common.config import config
from util.thread import SyncTask

class CoverParser(AdditionalParserBase):
    def __init__(self, task_info: TaskInfo):
        super().__init__(task_info)

    def parse(self):
        suffix = config.get(config.cover_type).value
        contents = self._get_cover_contents(suffix)

        self._write(contents, suffix = suffix)

    def _get_cover_contents(self, suffix: str):
        def on_success(response: bytes):
            nonlocal contents

            contents = response
            
        def on_error(error_message: str):
            nonlocal error_msg

            error_msg = error_message
        
        contents = None
        error_msg = None

        url = "{url}@.{suffix}".format(url = self.task_info.Episode.cover, suffix = suffix)

        worker = NetworkRequestWorker(url, response_type = ResponseType.BYTES)
        worker.success.connect(on_success)
        worker.error.connect(on_error)

        if error_msg:
            self._on_error(error_msg)

        SyncTask.run(worker)

        return contents
