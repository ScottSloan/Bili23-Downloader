"""
在后台线程里跑 FFmpeg，结果经调度层回调

`process.py` 的 `run()` 是阻塞的，这里给它配一个线程壳与三个回调，供需要「发起后继续做别的事」
的调用方使用（`downloader/merger.py` 就是这么用的）。

**不依赖 Qt，两端共用。** 回调不在工作线程上直接执行，而是交给 `thread/dispatch.py`：
桌面侧投递回 GUI 线程，服务端侧推进事件队列。这正是 S2-0 建那一层的原因 ——
合并完成后要改 TaskInfo、发 signal_bus、重命名文件，这些在桌面版必须回到 GUI 线程。

与它取代的 `FFmpegRunner(QThread)` 相比还少一类风险：QThread 在仍然运行时被析构会让 Qt
直接 qFatal 中止进程，本仓库为此在 downloader / merger 两处都写了防护。普通线程没有这个问题。
"""

from typing import Callable, List, Optional
import logging
import threading

from ..common.translator import Translator
from ..thread.dispatch import dispatch

from .command import FFmpegCommand
from .process import FFmpegProcess

logger = logging.getLogger(__name__)

class FFmpegTask:
    def __init__(self, cmd: List[str],
                 on_progress: Callable[[int], None] = None,
                 on_finished: Callable[[int, str, str], None] = None,
                 on_error: Callable[[Exception, str, str], None] = None):
        self._on_progress = on_progress
        self._on_finished = on_finished
        self._on_error = on_error

        # 进度回调同样要过调度层：它在读 stdout 的那个线程上产生，
        # 而桌面侧的接收方要更新界面
        self._process = FFmpegProcess(cmd, on_progress = self._dispatch_progress)

        self._thread: Optional[threading.Thread] = None

    @classmethod
    def from_command(cls, command: FFmpegCommand, **kwargs):
        return cls(command.build(), **kwargs)

    def set_cwd(self, cwd):
        self._process.set_cwd(str(cwd) if cwd is not None else None)

        return self

    def set_duration(self, duration: float):
        """预设媒体总时长（秒），用于在 FFmpeg 打印出 Duration 之前就能换算百分比"""
        self._process.set_duration(duration)

        return self

    def start(self) -> None:
        # daemon：进程退出时不因为它而挂住。正常路径上 stop() 会先终止子进程并 join，
        # 这里只是兜住「退出流程没走到」的极端情况
        self._thread = threading.Thread(target = self._run, name = "ffmpeg-task", daemon = True)

        self._thread.start()

    def _run(self) -> None:
        result = self._process.run()

        # 还没建起子进程就被要求停止。既不算成功也不算失败，什么都不回调 ——
        # 回调出去会让调用方误以为这一步结束了
        if result.aborted:
            return

        if result.error is not None:
            self._report_error(
                RuntimeError(Translator.ERROR_MESSAGES("FFMPEG_FAILED")), result)

            return

        # **返回码非 0 走的是错误分支，不是完成分支。**
        # 原先这套判断在 FFmpegRunner 里，调用方（Merger）只连了 finished/error 两个信号，
        # 把非零返回码当成完成会让它继续去重命名一个根本没生成的文件
        if result.return_code != 0:
            self._report_error(
                RuntimeError(Translator.ERROR_MESSAGES("FFMPEG_FAILED_WITH_CODE").format(
                    code = result.return_code)),
                result)

            return

        if self._on_finished is not None:
            dispatch(self._on_finished, result.return_code, result.stdout, result.stderr)

    def _report_error(self, error: Exception, result) -> None:
        if self._on_error is not None:
            dispatch(self._on_error, error, result.stdout, result.stderr)

    def _dispatch_progress(self, progress: int) -> None:
        if self._on_progress is not None:
            dispatch(self._on_progress, progress)

    def is_running(self) -> bool:
        return self._thread is not None and self._thread.is_alive()

    def stop(self, timeout: float = 3.0) -> bool:
        """
        终止 FFmpeg 子进程并等待线程收尾，返回线程是否已退出

        子进程被终止后管道随即 EOF，读取循环自己就能干净收尾，所以这里只需等待。
        超时返回 False，调用方**不要**因此去强杀线程 —— 强行终止线程在 Windows 上
        可能在持有 CRT 堆锁时发生，之后任何一次 free 都会崩溃
        """
        self._process.stop()

        thread = self._thread

        if thread is None:
            return True

        thread.join(timeout)

        if thread.is_alive():
            logger.warning("FFmpeg 线程在 %.1f 秒内未退出", timeout)

            return False

        return True
