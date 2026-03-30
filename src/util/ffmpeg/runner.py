from util.ffmpeg import FFmpegCommand
from util.common import Translator

from typing import Optional, Callable, List
import subprocess
import threading
import sys

class FFmpegRunner:
    def __init__(self, cmd: List[str]):
        self._cmd = cmd
        self._cwd = None
        self._proc: Optional[subprocess.Popen] = None
        self._thread: Optional[threading.Thread] = None

        self._on_completed: Optional[Callable[[int, str, str], None]] = None
        self._on_error: Optional[Callable[[Exception, str, str], None]] = None

    @classmethod
    def from_command(cls, command: FFmpegCommand):
        return cls(command.build())

    def run(self):
        return_code = -1
        stdout = ""
        stderr = ""
        exception = None

        try:
            kwargs = {}

            # 隐藏 Windows 平台的命令行窗口
            if sys.platform == "win32":
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
            if self._on_error:
                self._on_error(RuntimeError(Translator.ERROR_MESSAGES("FFMPEG_FAILED")), stdout, stderr)

                return

        if return_code == 0:
            if self._on_completed:
                self._on_completed(return_code, stdout, stderr)
        else:
            if self._on_error:
                self._on_error(RuntimeError(Translator.ERROR_MESSAGES("FFMPEG_FAILED_WITH_CODE").format(code = return_code)), stdout, stderr)

    def start(self):
        self._thread = threading.Thread(target = self.run, name = "FFmpegRunner", daemon = True)
        self._thread.start()

        return self
    
    def wait(self):
        if self._thread:
            self._thread.join()

    def terminate(self):
        if self._proc:
            self._proc.terminate()

    def set_cwd(self, cwd: str):
        self._cwd = cwd

        return self

    def on_completed(self, callback: Callable[[int, str, str], None]):
        '''
        设置完成回调
        return_code: int, stdout: str, stderr: str
        '''
        self._on_completed = callback

        return self

    def on_error(self, callback: Callable[[Exception, str, str], None]):
        """
        设置错误回调
        exception: Exception, stdout: str, stderr: str
        """
        self._on_error = callback

        return self
