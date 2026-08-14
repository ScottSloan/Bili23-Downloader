from ...download.task.info import TaskInfo
from ..parser.base import ParserBase

from pathlib import Path
from typing import List

class AdditionalParserBase(ParserBase):
    def __init__(self, task_info: TaskInfo):
        super().__init__()

        self.task_info: TaskInfo = task_info

    def _write(self, contents: str | bytes, suffix: str, name: str = None, qualifier: List[str] = None):
        if isinstance(contents, str):
            mode = "w"
            encoding = "utf-8"

        elif isinstance(contents, bytes):
            mode = "wb"
            encoding = None

        if name is None:
            name = self.task_info.File.name

        if qualifier:
            name_parts = f"{name}.{'.'.join(qualifier)}"
        else:
            name_parts = name

        path = self.__base_path / f"{name_parts}.{suffix}"
        path.parent.mkdir(parents = True, exist_ok = True)

        with open(path, mode, encoding = encoding) as f:
            f.write(contents)

        self._update_file_size(path)

        return path.name

    @staticmethod
    def is_embed_available(task_info: TaskInfo):
        # 只有 MKV 原生支持 ASS 字幕轨，MP4 无法容纳
        # merge_file_ext 仅在存在合并步骤时才会被赋值，因此这一个判断同时覆盖了
        # 「输出容器为 MKV」与「存在 FFmpeg 合并步骤」两个前提
        return task_info.File.merge_file_ext == "mkv"

    def _add_subtitle_track(self, file_name: str, title: str, language: str = "", kind: str = "subtitle"):
        # 登记待嵌入的字幕轨，Merger 在合并阶段据此拼接 FFmpeg 命令
        self.task_info.File.subtitle_track_list.append({
            "file": file_name,
            "title": title,
            "language": language,
            "kind": kind
        })

    def _update_file_size(self, path: Path):
        if path.exists():
            self.task_info.Download.downloaded_size += path.stat().st_size
            self.task_info.Download.total_size += path.stat().st_size

    def _on_error(self, error_message: str):
        raise RuntimeError(error_message)
    
    @property
    def __base_path(self):
        return Path(self.task_info.File.download_path, self.task_info.File.folder)
