from ...common.translator import Translator
from ...common.enum import MetadataType
from ...common._json import dumps
from ...download.task.options import resolve

from ...network.request import SyncNetWorkRequest, ResponseType
from ...download.task.info import TaskInfo
from ..episode.tree import Attribute

from .file.metadata_nfo import MetadataNFO
from .base import AdditionalParserBase

from dataclasses import asdict
from pathlib import Path
import logging

logger = logging.getLogger(__name__)

class MetadataParser(AdditionalParserBase):
    def __init__(self, task_info: TaskInfo):
        super().__init__(task_info)

    def parse(self):
        episode = self.task_info.Episode

        if episode.attribute & Attribute.VIDEO_BIT and episode.bvid:
            from httpx import HTTPError

            if episode.attribute & Attribute.COLLECTION_BIT:
                # 合集条目不能复用入口稿件的简介：合集里所有条目共用入口稿件的 episode_id，
                # 任务里带的简介是入口稿件的那一份（#498），只能按当前 BV 重新查
                try:
                    self._get_video_description()

                except (HTTPError, RuntimeError, ValueError):
                    # 查不到就留空，宁缺也不能把别的稿件的简介写进去。
                    # 也不能让异常冒出去：这一步排在音视频下载完成之后，下载大合集时每一集都要
                    # 多发一次请求，被风控拦下就会让已下载完成的任务整个判为失败（同 #488）
                    episode.description = ""

                    logger.warning("无法获取合集条目 %s 的简介，已留空", episode.bvid, exc_info = True)

            elif not episode.description:
                # 解析缓存失效时，按当前 BV 补查缺失的简介。
                try:
                    self._get_video_description()
                except (HTTPError, RuntimeError, ValueError):
                    logger.warning("无法补取视频 %s 的简介", episode.bvid, exc_info = True)

            try:
                self._get_video_tags()
            except (HTTPError, RuntimeError, ValueError):
                logger.warning("无法获取视频 %s 的标签", episode.bvid, exc_info = True)

        match resolve(self.task_info, "metadata_type"):
            case MetadataType.NFO:
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

        return dumps(filtered_data, indent = 2)

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

        self.check_response(response)
        tags = response.get("data")
        if not isinstance(tags, list):
            raise ValueError("Invalid video tag response")

        names = (tag.get("tag_name") for tag in tags if isinstance(tag, dict))
        self.task_info.Episode.tags = [name for name in names if isinstance(name, str) and name]

    def _get_video_description(self):
        params = {"bvid": self.task_info.Episode.bvid}
        url = f"https://api.bilibili.com/x/web-interface/wbi/view?{self.enc_wbi(params)}"

        request = SyncNetWorkRequest(url)
        response = request.run()
        self.check_response(response)

        data = response.get("data")
        if not isinstance(data, dict) or data.get("bvid") != self.task_info.Episode.bvid or not isinstance(data.get("desc"), str):
            raise ValueError("Invalid video description response")

        self.task_info.Episode.description = data["desc"]
