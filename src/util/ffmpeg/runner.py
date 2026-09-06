"""
FFmpeg 的 Qt 线程包装

**这个模块只属于桌面侧。** 真正跑进程、解析进度的逻辑在 `process.py`（不依赖 Qt），
这里只是把它放进 QThread 并把结果转成信号。

服务端侧不要用这个类：Qt 信号的跨线程投递需要 Qt 事件循环，而 WebUI 跑的是 asyncio（D16）。
那边直接 `await asyncio.to_thread(FFmpegProcess(...).run)`，进度回调用
`FFmpegProcess(cmd, on_progress = ...)` 传进去。
"""

from typing import List

from PySide6.QtCore import QThread, Signal

from ..common.translator import Translator

from .command import FFmpegCommand
from .process import FFmpegProcess

class FFmpegRunner(QThread):
    finished_signal = Signal(int, str, str)  # return_code, stdout, stderr
    error_signal = Signal(Exception, str, str)  # exception, stdout, stderr
    progress_signal = Signal(int)  # 0 - 100

    def __init__(self, cmd: List[str], parent = None):
        super().__init__(parent)

        self._process = FFmpegProcess(cmd, on_progress = self.progress_signal.emit)

    @classmethod
    def from_command(cls, command: FFmpegCommand, parent = None):
        return cls(command.build(), parent = parent)

    def set_cwd(self, cwd: str):
        self._process.set_cwd(cwd)

        return self

    def set_duration(self, duration: float):
        """
        预设媒体总时长（秒），用于在 FFmpeg 打印出 Duration 之前就能换算百分比

        解析到 FFmpeg 自己报的时长后会以后者为准，这里只是兜底
        """
        self._process.set_duration(duration)

        return self

    def run(self):
        result = self._process.run()

        # 线程刚启动就被要求停止，子进程根本没建起来。既不算成功也不算失败，
        # 什么信号都不发 —— 发出去只会让 Merger 误以为合并结束
        if result.aborted:
            return

        if result.error is not None:
            self.error_signal.emit(
                RuntimeError(Translator.ERROR_MESSAGES("FFMPEG_FAILED")),
                result.stdout, result.stderr
            )

            return

        if result.return_code == 0:
            self.finished_signal.emit(result.return_code, result.stdout, result.stderr)

        else:
            self.error_signal.emit(
                RuntimeError(Translator.ERROR_MESSAGES("FFMPEG_FAILED_WITH_CODE").format(code = result.return_code)),
                result.stdout, result.stderr
            )

    def stop(self, timeout: int = 3000):
        """
        终止 FFmpeg 子进程并等待线程收尾，返回线程是否已退出

        绝不调用 QThread.terminate()：它在 Windows 上就是 TerminateThread，
        会在任意指令处杀死线程，若当时正持有 CRT 堆锁，之后任何一次 free 都会崩溃。
        子进程被终止后管道随即 EOF，读取循环自己就能干净收尾。
        """
        self._process.stop()

        return self.wait(timeout)
