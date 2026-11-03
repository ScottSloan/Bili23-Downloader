"""On-demand inspection of completed outputs, outside the merge queue."""
from copy import deepcopy
from pathlib import Path
from threading import Event

from PySide6.QtCore import Signal, Slot, Qt
from PySide6.QtWidgets import QDialog, QVBoxLayout, QLabel, QPlainTextEdit, QPushButton

from util.common.config import config
from util.common.enum import FFmpegSource, DownloadType
from util.common.io.directory import Directory
from util.download.task.manager import task_manager
from util.media_probe import find_ffprobe, probe_media
from util.thread.async_ import AsyncTask
from util.thread.worker_base import WorkerBase
import shutil
import logging

logger = logging.getLogger(__name__)


class InspectionWorker(WorkerBase):
    result = Signal(dict)

    def __init__(self, paths, executable, cancel, task_id):
        super().__init__()
        self.paths = paths
        self.executable = executable
        self.cancel = cancel
        self.task_id = task_id

    @Slot()
    def run(self):
        try:
            results = []
            for path, expectations in self.paths:
                if self.cancel.is_set():
                    break
                result = probe_media(path, executable=self.executable, cancel=self.cancel, **expectations)
                results.append({"file": path.name, **result.to_dict()})
            if not self.cancel.is_set():
                result = {"files": results}
                try:
                    task_manager.save_verification(self.task_id, deepcopy(result)).result()
                    result["saved"] = True
                except Exception:
                    logger.exception("Could not save media inspection")
                    result["saved"] = False
                self.result.emit(result)
        except Exception:
            logger.exception("Media inspection failed")
            if not self.cancel.is_set():
                self.result.emit({"files": [], "reason": "inspection_error"})
        finally:
            self.finished.emit()


class MediaInspectionDialog(QDialog):
    def __init__(self, task, parent=None):
        super().__init__(parent)
        self.task = task
        self.cancel = Event()
        self.worker = None
        self.setWindowTitle(self.tr("Media inspection"))
        self.resize(640, 480)
        layout = QVBoxLayout(self)
        label = QLabel(self.tr("Quick structure inspection. This does not decode the entire file."))
        label.setWordWrap(True)
        layout.addWidget(label)
        self.output = QPlainTextEdit(self)
        self.output.setReadOnly(True)
        self.output.setPlainText(self.formatResult(task.File.verification)
                                 if task.File.verification else self.tr("Not inspected"))
        layout.addWidget(self.output)
        self.inspect = QPushButton(self.tr("Inspect"), self)
        self.inspect.clicked.connect(self.startInspection)
        layout.addWidget(self.inspect)
        self.finished.connect(self.onClosed)

    def formatResult(self, result):
        statuses = {"verified": self.tr("Structure verified"), "warning": self.tr("Needs review"),
                    "failed": self.tr("Inspection failed"), "unverified": self.tr("Not verified")}
        reasons = {"ffprobe_missing": self.tr("Install ffprobe alongside FFmpeg or add it to PATH, then retry"),
                   "ffprobe_unavailable": self.tr("ffprobe could not be started"),
                   "file_missing": self.tr("File not found"), "timeout": self.tr("Inspection timed out"),
                   "probe_failed": self.tr("File could not be read"),
                   "missing_required_stream": self.tr("Required media track is missing")}
        lines = []
        for item in result.get("files", []):
            lines.extend([item["file"], statuses.get(item["status"], self.tr("Not verified"))])
            if item.get("reason"):
                lines.append(reasons.get(item["reason"], self.tr("Inspection could not be completed")))
            for warning in item.get("warnings", []):
                lines.append(self.tr("Duration differs from the expected value. Check the source and file.")
                             if warning == "duration_mismatch" else self.tr("Media specifications need review"))
            if item.get("duration"):
                lines.append(self.tr("Duration: %s seconds") % round(item["duration"], 2))
            for stream in item.get("streams", []):
                details = [stream.get("codec") or self.tr("Unknown codec")]
                if stream.get("width") and stream.get("height"):
                    details.append(f"{stream['width']} × {stream['height']}")
                if stream.get("sample_rate"):
                    details.append(f"{stream['sample_rate']} Hz")
                if stream.get("channels"):
                    details.append(self.tr("%s channels") % stream["channels"])
                if stream.get("bit_rate"):
                    details.append(f"{round(stream['bit_rate'] / 1000)} kb/s")
                lines.append(" · ".join(details))
            lines.append("")
        if result.get("reason") == "inspection_error":
            lines.append(self.tr("Inspection encountered an error. Please retry."))
        if result.get("saved") is False:
            lines.append(self.tr("Could not save results. They remain visible in this window; retry to save."))
        elif result.get("saved"):
            lines.append(self.tr("Results saved"))
        return "\n".join(lines) or self.tr("No media outputs recorded")

    @Slot()
    def startInspection(self):
        if self.worker is not None:
            return
        self.cancel.clear()
        self.inspect.setEnabled(False)
        self.output.setPlainText(self.tr("Inspecting…"))
        # Inspect recorded final media files, including separate audio/video outputs.
        extensions = {".mp4", ".mkv", ".m4a", ".mp3", ".flac", ".ec3", ".aac", ".flv", ".wav"}
        root = Path(self.task.File.download_path, self.task.File.folder)
        paths = []
        audio_extensions = {".m4a", ".mp3", ".flac", ".ec3", ".aac", ".wav"}
        media = [name for name in self.task.File.relative_files if Path(name).suffix.lower() in extensions]
        for index, name in enumerate(media):
            is_audio = Path(name).suffix.lower() in audio_extensions
            merged = self.task.Download.merge_video_audio and index == 0 and not is_audio
            paths.append((root / name, {
                "expect_video": bool(self.task.Download.type & DownloadType.VIDEO) and not is_audio,
                "expect_audio": bool(self.task.Download.type & DownloadType.AUDIO) and (is_audio or merged),
            }))
        if not paths:
            self.onResult({"files": [], "reason": "no_media_outputs"})
            return
        ffmpeg = str(Directory.get_cwd() / "bundle" / "ffmpeg")
        if config.get(config.ffmpeg_source) == FFmpegSource.SYSTEM:
            ffmpeg = shutil.which("ffmpeg")
        elif config.get(config.ffmpeg_source) == FFmpegSource.CUSTOM:
            ffmpeg = config.get(config.custom_ffmpeg_path)
        self.worker = InspectionWorker(paths, find_ffprobe(ffmpeg), self.cancel, self.task.Basic.task_id)
        self.worker.result.connect(self.onResult, Qt.ConnectionType.QueuedConnection)
        AsyncTask.run(self.worker)

    @Slot(dict)
    def onResult(self, result):
        if self.cancel.is_set():
            return
        self.worker = None
        self.task.File.verification = deepcopy(result)
        self.output.setPlainText(self.formatResult(result))
        self.inspect.setEnabled(True)

    @Slot(int)
    def onClosed(self, result):
        self.cancel.set()
