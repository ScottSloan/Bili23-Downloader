from util.parse.additional import MetadataNFO, AdditionalParserBase
from util.network import SyncNetWorkRequest, ResponseType
from util.parse.episode.tree import Attribute
from util.common import config, Translator
from util.common.enum import MetadataType

from ...download.task.info import TaskInfo

from dataclasses import asdict
from pathlib import Path
import json

class MetadataParser(AdditionalParserBase):
    def __init__(self, task_info: TaskInfo):
        super().__init__(task_info)

    def parse(self):
        match config.get(config.metadata_type):
            case MetadataType.NFO:
                if self.task_info.Episode.attribute & Attribute.VIDEO_BIT != 0:
                    # 投稿视频需要额外获取 tag 和 category 信息
                    self._get_video_tags()

                self._to_nfo()
                
            case MetadataType.JSON:
                contents = self._to_json()

                self._write(contents, suffix = "json", name = self.task_info.File.name, qualifier = [Translator.ADDITIONAL_FILES_QUALIFIER("METADATA")])

    def _to_nfo(self):
        contents_list = MetadataNFO(self.task_info).generate()

        for entry in contents_list:
            contents, name, qualifier = entry["contents"], entry["name"], entry["qualifier"]

            # 去除 contents 中多余空行
            contents = "\n".join([line for line in contents.splitlines() if line.strip() != ""])

            self._write(contents, suffix = "nfo", name = name, qualifier = qualifier)

        self._save_poster()

    def _to_json(self):
        data = asdict(self.task_info.Episode)

        # 过滤掉空值
        filtered_data = {k: v for k, v in data.items() if v not in [None, "", [], {}, 0]}

        return json.dumps(filtered_data, ensure_ascii = False, indent = 4)

    def _save_poster(self):
        path = Path(self.task_info.File.download_path, self.task_info.File.folder, "poster.jpg")

        if not path.exists() and self.task_info.Episode.poster:

            request = SyncNetWorkRequest(self.task_info.Episode.poster, response_type = ResponseType.BYTES)
            response = request.run()

            self._write(response, suffix = "jpg", name = "poster")

    def _get_video_tags(self):            
        url = "https://api.bilibili.com/x/web-interface/view/detail/tag?bvid={bvid}".format(bvid = self.task_info.Episode.bvid)

        request = SyncNetWorkRequest(url)
        response = request.run()

        tag_list = response.get("data", [])
            
        self.task_info.Episode.tags = [tag.get("tag_name") for tag in tag_list]
