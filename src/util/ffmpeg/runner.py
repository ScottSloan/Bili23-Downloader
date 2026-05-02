from util.common import Translator

from .command import FFmpegCommand

from typing import Optional, List
import subprocess
import os

from PySide6.QtCore import QThread, Signal

class FFmpegRunner(QThread):
    finished_signal = Signal(int, str, str)  # return_code, stdout, stderr
    error_signal = Signal(Exception, str, str)  # exception, stdout, stderr

    def __init__(self, cmd: List[str], parent=None):
        super().__init__(parent)
        self._cmd = cmd
        self._cwd = None
        self._proc: Optional[subprocess.Popen] = None

    @classmethod
    def from_command(cls, command: FFmpegCommand, parent=None):
        return cls(command.build(), parent=parent)

    def set_cwd(self, cwd: str):
        self._cwd = cwd
        return self

    def run(self):
        return_code = -1
        stdout = ""
        stderr = ""
        exception = None

        try:
            kwargs = {}

            if os.name == "nt":
                kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

            self._proc = subprocess.Popen(
                self._cmd,
                stdout = subprocess.PIPE,
                stderr = subprocess.PIPE,
                cwd = self._cwd,
                text = True,
                encoding = "utf-8",
                errors = "replace",
                **kwargs
            )

            stdout, stderr = self._proc.communicate()
            return_code = self._proc.returncode

        except Exception as e:
            exception = e
            stdout = ""
            stderr = str(e)

        finally:
            if self._proc and self._proc.poll() is None:
                self._proc.terminate()

            self._proc = None

        if exception:
            self.error_signal.emit(RuntimeError(Translator.ERROR_MESSAGES("FFMPEG_FAILED")), stdout, stderr)
            return

        if return_code == 0:
            self.finished_signal.emit(return_code, stdout, stderr)
        else:
            self.error_signal.emit(RuntimeError(Translator.ERROR_MESSAGES("FFMPEG_FAILED_WITH_CODE").format(code = return_code)), stdout, stderr)

    def terminate(self):
        if self._proc:
            self._proc.terminate()

        super().terminate()
