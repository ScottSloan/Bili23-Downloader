from ..common.translator import Translator

from .command import FFmpegCommand

from typing import Optional, List
from threading import Lock
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

        # 保护「创建子进程」与「请求终止」这一对操作。二者分处两个线程，
        # 若 stop() 抢在 Popen 之前完成，终止请求就会落空，线程会一直跑到 FFmpeg 自己结束
        self._proc_lock = Lock()
        self._stop_requested = False

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

            with self._proc_lock:
                if self._stop_requested:
                    # 线程刚启动就被要求停止，此时还没有子进程可以终止，直接收工
                    return

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

    def stop(self, timeout: int = 3000):
        """
        终止 FFmpeg 子进程并等待线程收尾，返回线程是否已退出

        绝不调用 QThread.terminate()：它在 Windows 上就是 TerminateThread，
        会在任意指令处杀死线程，若当时正持有 CRT 堆锁，之后任何一次 free 都会崩溃。
        子进程被终止后 communicate() 会立即返回，线程自己就能干净收尾。
        """
        with self._proc_lock:
            # 在锁内置位：本次若抢在 Popen 之前，run() 会读到标记并放弃启动子进程
            self._stop_requested = True

            proc = self._proc

        if proc is not None:
            try:
                proc.terminate()

            except Exception:
                # 子进程可能刚好已经退出，此时 terminate 会失败，忽略即可
                pass

        return self.wait(timeout)
