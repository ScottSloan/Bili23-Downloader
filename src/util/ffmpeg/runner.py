from util.ffmpeg import FFmpegCommand
from util.common import Translator

from typing import Optional, List
import subprocess
import os
import re
import threading

from PySide6.QtCore import QThread, Signal

class FFmpegRunner(QThread):
    finished_sig = Signal(int, str, str)
    error_sig = Signal(Exception, str, str)
    progress_sig = Signal(float)

    def __init__(self, cmd: List[str], parent=None):
        super().__init__(parent)
        self._cmd = cmd
        self._cwd = None
        self._proc: Optional[subprocess.Popen] = None
        self._total_duration: Optional[float] = None

    @classmethod
    def from_command(cls, command: FFmpegCommand, parent=None):
        return cls(command.build(), parent=parent)

    def set_cwd(self, cwd: str):
        self._cwd = cwd
        return self

    def _parse_duration(self, line: str) -> Optional[float]:
        match = re.search(r"Duration:\s*(\d+):(\d+):(\d+)\.(\d+)", line)
        if match:
            hours, minutes, seconds, centiseconds = map(int, match.groups())
            return hours * 3600 + minutes * 60 + seconds + centiseconds / 100
        return None

    def _parse_time(self, line: str) -> Optional[float]:
        match = re.search(r"time=(\d+):(\d+):(\d+)\.(\d+)", line)
        if match:
            hours, minutes, seconds, centiseconds = map(int, match.groups())
            return hours * 3600 + minutes * 60 + seconds + centiseconds / 100
        return None

    def run(self):
        return_code = -1
        stdout_lines = []
        stderr_lines = []
        exception = None

        try:
            kwargs = {}

            if os.name == "nt":
                kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

            self._proc = subprocess.Popen(
                self._cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                cwd=self._cwd,
                text=True,
                encoding="utf-8",
                errors="replace",
                bufsize=1,
                **kwargs
            )

            def read_stream(stream, lines_list):
                for line in iter(stream.readline, ""):
                    lines_list.append(line)

            stdout_thread = threading.Thread(
                target=read_stream, args=(self._proc.stdout, stdout_lines), daemon=True
            )
            stderr_thread = threading.Thread(
                target=read_stream, args=(self._proc.stderr, stderr_lines), daemon=True
            )
            stdout_thread.start()
            stderr_thread.start()

            last_progress = -1.0
            while self._proc.poll() is None:
                new_lines = stderr_lines[:]
                for line in new_lines:
                    if self._total_duration is None:
                        self._total_duration = self._parse_duration(line)

                    current_time = self._parse_time(line)
                    if current_time is not None and self._total_duration is not None and self._total_duration > 0:
                        progress = min((current_time / self._total_duration) * 100, 99.5)
                        if abs(progress - last_progress) >= 0.5:
                            last_progress = progress
                            self.progress_sig.emit(progress)

                self.msleep(100)

            stdout_thread.join()
            stderr_thread.join()

            stdout = "".join(stdout_lines)
            stderr = "".join(stderr_lines)
            return_code = self._proc.returncode

        except Exception as e:
            exception = e
            stdout = "".join(stdout_lines)
            stderr = "".join(stderr_lines)

        finally:
            if self._proc and self._proc.poll() is None:
                self._proc.terminate()

            self._proc = None

        if exception:
            self.error_sig.emit(RuntimeError(Translator.ERROR_MESSAGES("FFMPEG_FAILED")), stdout, stderr)
            return

        if return_code == 0:
            self.progress_sig.emit(100.0)
            self.finished_sig.emit(return_code, stdout, stderr)
        else:
            self.error_sig.emit(RuntimeError(Translator.ERROR_MESSAGES("FFMPEG_FAILED_WITH_CODE").format(code=return_code)), stdout, stderr)

    def terminate(self):
        if self._proc:
            self._proc.terminate()

        super().terminate()