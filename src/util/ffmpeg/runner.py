from ..common.translator import Translator

from .command import FFmpegCommand

from typing import Optional, List
from collections import deque
from threading import Lock, Thread
import subprocess
import re
import os

from PySide6.QtCore import QThread, Signal

# 总时长只有 stderr 上的输入信息里有，-progress 不提供，因此仍要从这里解析
_DURATION_PATTERN = re.compile(r"Duration:\s*(\d+):(\d{2}):(\d{2})\.(\d+)")

# -progress 每个周期输出一组 key=value，其中这一项是已处理的微秒数
_PROGRESS_TIME_KEY = "out_time_us="

# 两边都只留尾部。加了 -nostats 之后 stderr 已经没有进度行刷屏，
# 但个别警告仍可能反复出现；stdout 那边则整个都是进度，留存价值更低
_STDERR_KEEP_LINES = 500
_STDOUT_KEEP_LINES = 40

class FFmpegRunner(QThread):
    finished_signal = Signal(int, str, str)  # return_code, stdout, stderr
    error_signal = Signal(Exception, str, str)  # exception, stdout, stderr
    progress_signal = Signal(int)  # 0 - 100

    def __init__(self, cmd: List[str], parent = None):
        super().__init__(parent)
        self._cmd = cmd
        self._cwd = None
        self._proc: Optional[subprocess.Popen] = None

        self._duration = 0.0
        self._last_progress = -1

        # 保护「创建子进程」与「请求终止」这一对操作。二者分处两个线程，
        # 若 stop() 抢在 Popen 之前完成，终止请求就会落空，线程会一直跑到 FFmpeg 自己结束
        self._proc_lock = Lock()
        self._stop_requested = False

    @classmethod
    def from_command(cls, command: FFmpegCommand, parent = None):
        return cls(command.build(), parent = parent)

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

            stdout, stderr = self._read_output(self._proc)

            return_code = self._proc.wait()

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
        主线程逐行读 stdout 上的进度，后台线程同时读 stderr

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

            self.progress_signal.emit(progress)

    @staticmethod
    def _to_seconds(match: re.Match):
        hours, minutes, seconds, fraction = match.groups()

        return int(hours) * 3600 + int(minutes) * 60 + int(seconds) + int(fraction) / (10 ** len(fraction))

    def stop(self, timeout: int = 3000):
        """
        终止 FFmpeg 子进程并等待线程收尾，返回线程是否已退出

        绝不调用 QThread.terminate()：它在 Windows 上就是 TerminateThread，
        会在任意指令处杀死线程，若当时正持有 CRT 堆锁，之后任何一次 free 都会崩溃。
        子进程被终止后管道随即 EOF，读取循环自己就能干净收尾。
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
