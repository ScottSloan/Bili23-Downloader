from ...common.enum import DownloadType

from ...download.task.info import TaskInfo

from .base import AdditionalParserBase

from pathlib import Path
from typing import List
import logging

logger = logging.getLogger(__name__)

class ChapterParser(AdditionalParserBase):
    def __init__(self, task_info: TaskInfo):
        super().__init__(task_info)

    @staticmethod
    def get_file_name(task_id: str):
        # 章节文件仅作为 FFmpeg 的中间文件，Merger 通过同样的名称找到并在合并后删除
        return "chapter_{task_id}.txt".format(task_id = task_id)

    @staticmethod
    def is_available(task_info: TaskInfo):
        # 章节信息通过 FFmpeg 写入最终文件，因此只有存在合并步骤时才需要处理
        if task_info.Download.type & DownloadType.CHAPTER == 0:
            return False

        return task_info.Download.merge_video_audio or task_info.Download.video_parts_count > 0

    def parse(self, player_data: dict):
        view_points = player_data.get("view_points") or []

        if not view_points:
            # 绝大多数视频没有分段章节，此时不生成章节文件，合并流程也不会带上相关参数
            return

        contents = self._to_ffmetadata(view_points)

        self._write_chapter_file(contents)

    def _to_ffmetadata(self, view_points: List[dict]):
        # FFmpeg 的 ffmetadata 格式，MP4 和 MKV 均通过该格式写入章节
        lines = [";FFMETADATA1", ""]

        for index, entry in enumerate(view_points):
            start = int(entry.get("from", 0))
            end = int(entry.get("to", 0))

            if end <= start:
                # 末段的 to 有可能为 0，用视频总时长兜底；仍无法确定时跳过该段
                end = self._get_fallback_end(view_points, index, start)

                if end <= start:
                    continue

            lines.extend([
                "[CHAPTER]",
                "TIMEBASE=1/1000",
                f"START={start * 1000}",
                f"END={end * 1000}",
                f"title={self._escape(entry.get('content', ''))}",
                ""
            ])

        return "\n".join(lines)

    def _get_fallback_end(self, view_points: List[dict], index: int, start: int):
        # 优先用下一段的起始时间，没有下一段时用视频总时长
        if index + 1 < len(view_points):
            return int(view_points[index + 1].get("from", 0))

        return self.task_info.Episode.duration

    def _escape(self, content: str):
        # ffmetadata 中 = ; # \ 和换行需要转义
        return "".join("\\" + char if char in "=;#\\\n" else char for char in content)

    def _write_chapter_file(self, contents: str):
        file_name = self.get_file_name(self.task_info.Basic.task_id)

        path = Path(self.task_info.File.download_path, self.task_info.File.folder, file_name)
        path.parent.mkdir(parents = True, exist_ok = True)

        # 不使用基类的 _write，避免中间文件的体积被计入下载进度
        with open(path, "w", encoding = "utf-8") as f:
            f.write(contents)

        logger.info(f"已生成章节文件：{path}")
