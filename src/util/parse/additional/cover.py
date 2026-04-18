from util.network import SyncNetWorkRequest, ResponseType
from util.parse.additional import AdditionalParserBase
from util.common import config

from ...download.task.info import TaskInfo

import httpx

class CoverParser(AdditionalParserBase):
    def __init__(self, task_info: TaskInfo):
        super().__init__(task_info)

    def parse(self):
        suffix = config.get(config.cover_type).value

        for i in range(3):
            try:
                contents = self._get_cover_contents(suffix)
                break
            except httpx.HTTPError:
                if i == 2:
                    raise

        else:
            return

        self._write(contents, suffix = suffix, name = self.task_info.File.name)

    def _get_cover_contents(self, suffix: str):
        url = "{url}@.{suffix}".format(url = self.task_info.Episode.cover, suffix = suffix)

        request = SyncNetWorkRequest(url, response_type = ResponseType.BYTES)
        response = request.run()
        
        return response