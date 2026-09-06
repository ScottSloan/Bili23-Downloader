"""
运行 FFmpeg 子进程并解析进度

本模块**不依赖 Qt**，两端共用。`run()` 是阻塞的：桌面侧由 `runner.py` 的 QThread 包装调用，
服务端侧 `await asyncio.to_thread(proc.run)` 即可（D16）。

进度回调 `on_progress` 在**调用 run() 的那个线程**里同步执行，本模块不做任何线程投递 ——
需要切回 GUI 线程或推进 asyncio 队列，由各自的包装层负责。
"""

from dataclasses import dataclass
from typing import Callable, List, Optional
from collections import deque
from threading import Lock, Thread
import subprocess
import re
import os

from .command import FFmpegCommand

# 总时长只有 stderr 上的输入信息里有，-progress 不提供，因此仍要从这里解析
_DURATION_PATTERN = re.compile(r"Duration:\s*(\d+):(\d{2}):(\d{2})\.(\d+)")

# -progress 每个周期输出一组 key=value，其中这一项是已处理的微秒数
_PROGRESS_TIME_KEY = "out_time_us="

# 两边都只留尾部。加了 -nostats 之后 stderr 已经没有进度行刷屏，
# 但个别警告仍可能反复出现；stdout 那边则整个都是进度，留存价值更低
_STDERR_KEEP_LINES = 500
_STDOUT_KEEP_LINES = 40

@dataclass
class FFmpegResult:
    """
    一次 FFmpeg 执行的结果

    异常不往外抛，而是收在 error 里 —— 调用方（QThread 包装 / asyncio 包装）都需要在
    出错时同时拿到已经读到的 stdout / stderr 来做诊断，抛异常会把这两样丢掉。
    """

    return_code: int = -1
    stdout: str = ""
    stderr: str = ""
    error: Optional[Exception] = None

    # 子进程还没来得及创建就被要求停止。此时既不算成功也不算失败，调用方应当直接收工
    aborted: bool = False

class FFmpegProcess:
    def __init__(self, cmd: List[str], on_progress: Callable[[int], None] = None):
        self._cmd = cmd
        self._cwd = None
        self._proc: Optional[subprocess.Popen] = None

        self._on_progress = on_progress

        self._duration = 0.0
        self._last_progress = -1

        # 保护「创建子进程」与「请求终止」这一对操作。二者分处两个线程，
        # 若 stop() 抢在 Popen 之前完成，终止请求就会落空，进程会一直跑到 FFmpeg 自己结束
        self._proc_lock = Lock()
        self._stop_requested = False

    @classmethod
    def from_command(cls, command: FFmpegCommand, on_progress: Callable[[int], None] = None):
        return cls(command.build(), on_progress = on_progress)

    def set_cwd(self, cwd: str):
        self._cwd = cwd

        return self

    def set_duration(self, duration: float):
        """
        预设媒体总时长（秒），用于在 FFmpeg 打印出 Duration 之前就能换算百分比

        解析到 FFmpeg 自己报的时长后会以后者为准，这里只是兜底
        """
        if duration and duration > 0:
            self._duration = float(duration)

        return self

    def run(self) -> FFmpegResult:
        """阻塞执行，直到 FFmpeg 退出。不抛异常，结果全在 FFmpegResult 里"""
        result = FFmpegResult()

        try:
            kwargs = {}

            if os.name == "nt":
                kwargs["creationflags"] = getattr(subprocess, "CREATE_NO_WINDOW", 0x08000000)

            with self._proc_lock:
                if self._stop_requested:
                    # 刚要启动就被要求停止，此时还没有子进程可以终止，直接收工
                    result.aborted = True

                    return result

                self._proc = subprocess.Popen(
                    self._build_exec_command(),
                    stdout = subprocess.PIPE,
                    stderr = subprocess.PIPE,
                    # FFmpeg 默认会去读 stdin 响应交互按键，并为此打印一行 Press [q] to stop。
                    # 本进程没有控制台，这条输入通道只可能带来干扰，直接断掉
                    stdin = subprocess.DEVNULL,
                    cwd = self._cwd,
                    text = True,
                    encoding = "utf-8",
                    errors = "replace",
                    **kwargs
                )

            result.stdout, result.stderr = self._read_output(self._proc)

            result.return_code = self._proc.wait()

        except Exception as e:
            result.error = e
            result.stdout = ""
            result.stderr = str(e)

        finally:
            if self._proc and self._proc.poll() is None:
                self._proc.terminate()

            self._proc = None

        return result

    def _build_exec_command(self):
        """
        在原命令前插入进度参数

        -progress 把机器可读的进度写到 stdout；-nostats 关掉 stderr 上供人看的那一份，
        免得进度行把真正的诊断信息冲掉。两者都是全局选项，必须紧跟在可执行文件之后。

        pipe:1 依赖 FFmpeg 编译时启用了 pipe protocol，内置的那份已随 build.sh 一并开启；
        若换用自行编译的精简版而漏掉该 protocol，命令会直接失败
        """
        return [self._cmd[0], "-progress", "pipe:1", "-nostats", *self._cmd[1:]]

    def _read_output(self, proc: subprocess.Popen):
        """
        当前线程逐行读 stdout 上的进度，后台线程同时读 stderr

        不能再用 communicate()：它要等进程退出才一次性返回，过程中的进度拿不到。
        但两个管道必须同时有人读 —— 任意一个写满管道缓冲区都会把 FFmpeg 卡死在写调用上，
        这正是当初选用 communicate() 的原因，所以另一路仍要单独开线程。
        """
        stderr_lines = deque(maxlen = _STDERR_KEEP_LINES)

        def read_stderr():
            try:
                while True:
                    line = proc.stderr.readline()

                    if not line:
                        break

                    stderr_lines.append(line)

                    self._parse_duration(line)

            except Exception:
                # 进程被终止时管道会提前关闭，读失败无需处理
                pass

        stderr_thread = Thread(target = read_stderr, name = "ffmpeg-stderr", daemon = True)
        stderr_thread.start()

        stdout_lines = deque(maxlen = _STDOUT_KEEP_LINES)

        try:
            while True:
                # 不用 for line in proc.stdout：文本流的迭代带预读缓冲，
                # 进度要攒够一批才交出来，实时性就没了
                line = proc.stdout.readline()

                if not line:
                    break

                stdout_lines.append(line)

                self._parse_progress(line)

        except Exception:
            pass

        stderr_thread.join()

        for pipe in (proc.stdout, proc.stderr):
            try:
                pipe.close()

            except Exception:
                pass

        return "".join(stdout_lines), "".join(stderr_lines)

    def _parse_duration(self, line: str):
        # 合并阶段有视频、音频、封面等多路输入，每一路都会打印自己的 Duration，
        # 封面这类图片输入的时长极短，取最长的那一路才是输出文件的实际时长
        for match in _DURATION_PATTERN.finditer(line):
            duration = self._to_seconds(match)

            if duration > self._duration:
                self._duration = duration

    def _parse_progress(self, line: str):
        if not line.startswith(_PROGRESS_TIME_KEY):
            return

        value = line[len(_PROGRESS_TIME_KEY):].strip()

        # 还没有实际输出时这一项会是 N/A
        if not value.isdigit():
            return

        # _duration 由读 stderr 的那个线程写入。属性读写在 GIL 下是原子的，
        # 这里只要一份能用的快照，偶尔读到旧值也只是少算一格进度
        duration = self._duration

        if duration <= 0:
            return

        # 留出最后 1%：真正的收尾还有重命名、删除中间文件等步骤，
        # 先到 100% 再干等一会儿反而显得卡住
        progress = min(99, int(int(value) / 1_000_000 / duration * 100))

        if progress != self._last_progress:
            self._last_progress = progress

            if self._on_progress is not None:
                self._on_progress(progress)

    @staticmethod
    def _to_seconds(match: re.Match):
        hours, minutes, seconds, fraction = match.groups()

        return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(fraction) / (10 ** len(fraction))

    def stop(self) -> None:
        """
        终止 FFmpeg 子进程

        只管子进程，不等待读取线程 —— 子进程被终止后管道随即 EOF，
        `run()` 里的读取循环自己就能干净收尾。等待由调用方按各自的线程模型处理
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
