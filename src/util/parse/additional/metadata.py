from ...common.translator import Translator
from ...common.enum import MetadataType
from ...common._json import dumps
from ...download.task.options import resolve

from ...network.request import SyncNetWorkRequest, ResponseType
from ...download.task.info import TaskInfo
from ..episode.tree import Attribute

from .file.metadata_nfo import MetadataNFO
from .base import AdditionalParserBase

from PySide6.QtCore import QCoreApplication, QIODevice, QSaveFile
from httpx import HTTPError

from dataclasses import asdict
from json import loads
from pathlib import Path
import logging
import re

logger = logging.getLogger(__name__)

class MetadataParser(AdditionalParserBase):
    def __init__(self, task_info: TaskInfo):
        super().__init__(task_info)

    def parse(self, *, refresh = False):
        episode = self.task_info.Episode

        if episode.attribute & Attribute.VIDEO_BIT and episode.bvid:
            if refresh or episode.attribute & Attribute.COLLECTION_BIT:
                # 合集条目不能复用入口稿件的简介。
                self._get_video_description()
            elif not episode.description:
                # 解析缓存失效时，按当前 BV 补查缺失的简介。
                try:
                    self._get_video_description()
                except (HTTPError, RuntimeError, ValueError):
                    logger.warning("无法补取视频 %s 的简介", episode.bvid, exc_info = True)

            try:
                self._get_video_tags()
            except (HTTPError, RuntimeError, ValueError):
                if refresh:
                    raise
                logger.warning("无法获取视频 %s 的标签", episode.bvid, exc_info = True)

        match resolve(self.task_info, "metadata_type"):
            case MetadataType.NFO:
                self._to_nfo(refresh = refresh)
                
            case MetadataType.JSON:
                contents = self._to_json()

                self._write_metadata(contents, "json", self.task_info.File.name, [Translator.ADDITIONAL_FILES_QUALIFIER("METADATA")], refresh)

    def _to_nfo(self, *, refresh = False):
        contents_list = MetadataNFO(self.task_info).generate()

        for entry in contents_list:
            contents, name, qualifier = entry["contents"], entry["name"], entry["qualifier"]

            # 去除 contents 中多余空行
            contents = "\n".join([line for line in contents.splitlines() if line.strip() != ""])

            self._write_metadata(contents, "nfo", name, qualifier, refresh)

        if not refresh:
            self._save_poster()

    def _write_metadata(self, contents: str, suffix: str, name: str, qualifier: list[str], refresh: bool):
        if not refresh:
            self._write(contents, suffix = suffix, name = name, qualifier = qualifier)
            return

        directory = Path(self.task_info.File.download_path, self.task_info.File.folder)
        if not directory.is_absolute() or not directory.is_dir() or not name or Path(name).name != name:
            raise ValueError(Translator.ERROR_MESSAGES("FILE_NOT_FOUND_DETAIL"))

        path = directory / ".".join([name, *qualifier, suffix])
        # 用户可能在首次导出后切换了界面语言。原有侧车文件保留原名。
        candidates = [directory / f"{name}.{label}.{suffix}" for label in ("Metadata", "元数据", "元數據")]
        existing = [candidate for candidate in candidates if candidate.is_file()]
        if len(existing) > 1:
            raise ValueError(QCoreApplication.translate("RefreshMetadataDialog", "Multiple metadata files match this task"))
        if existing:
            path = existing[0]
            self._check_existing_bvid(path, suffix)

        file = QSaveFile(str(path))
        if not file.open(QIODevice.OpenModeFlag.WriteOnly):
            raise OSError(file.errorString())
        data = contents.encode("utf-8")
        if file.write(data) != len(data):
            file.cancelWriting()
            raise OSError(file.errorString())
        if not file.commit():
            raise OSError(file.errorString())

    def _check_existing_bvid(self, path: Path, suffix: str):
        contents = path.read_text(encoding = "utf-8-sig")
        if suffix == "json":
            data = loads(contents)
            bvid = data.get("bvid") if isinstance(data, dict) else None
        else:
            # 旧 NFO 可能含未转义的正文；仍可核对软件写入的 BV 标识。
            match = re.search(r'<uniqueid type="bvid">([^<]+)</uniqueid>', contents)
            bvid = match[1] if match else None

        if bvid != self.task_info.Episode.bvid:
            raise ValueError(QCoreApplication.translate("RefreshMetadataDialog", "Existing metadata belongs to a different or unknown video"))

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
