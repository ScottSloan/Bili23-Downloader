from ..common.translator import Translator

from .command import FFmpegCommand

from typing import Optional, List
from collections import deque
from threading import Lock, Thread, Event
import subprocess
import logging
import time
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

# 只要 FFmpeg 还在推进，-progress 每 0.5 秒就会写出一组数据，stderr 那边也时常有内容。
# 长时间一个字节都没有，说明它已经卡死在某次系统调用上（输出文件被外部扫描锁住、
# 目标落在休眠的外置盘或网络盘等），这种状态不会自愈。合并额度全局只有一个，
# 放任不管会让整条队列再也排不下去，因此必须主动终止
_NO_OUTPUT_TIMEOUT = 300.0

# 看门狗的巡检间隔，相对超时阈值足够密，又不至于空转太频繁
_WATCHDOG_INTERVAL = 5.0

logger = logging.getLogger(__name__)

class FFmpegRunner(QThread):
    finished_signal = Signal(int, str, str)  # return_code, stdout, stderr
    error_signal = Signal(Exception, str, str)  # exception, stdout, stderr
    progress_signal = Signal(int)  # 0 - 100

    def __init__(self, cmd: List[str], parent = None):
        super().__init__(parent)
        self._cmd = cmd
        self._cwd = None
        self._proc: Optional[subprocess.Popen] = None

        # FFmpeg 自报的时长与外部预设的兜底值分开存放：预设值来自上游接口，
        # 而各接口给的单位并不统一（部分是毫秒）。一旦把两者混在一起取最大值，
        # 被放大过的预设值就再也纠正不回来，进度会全程算成 0
        self._duration = 0.0
        self._probed_duration = 0.0
        self._last_progress = -1
        self._duration_warned = False

        # 看门狗：记录最后一次收到输出的时刻，长时间无输出即判定 FFmpeg 无响应
        self._last_output_time = 0.0
        self._watchdog_fired = False
        self._watchdog_stop = Event()

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

            self._last_output_time = time.monotonic()

            watchdog = self._start_watchdog(self._proc)

            try:
                stdout, stderr = self._read_output(self._proc)

                # 管道两端都已 EOF，进程通常正在退出；仍给一个上限，
                # 免得它卡在收尾的写操作上把本线程一起拖住
                return_code = self._wait_proc(self._proc)

            finally:
                self._watchdog_stop.set()
                watchdog.join(timeout = _WATCHDOG_INTERVAL * 2)

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

        if self._watchdog_fired:
            # 进程是被看门狗杀掉的，返回码只反映「被终止」，据此报「退出码 N」会误导用户
            self.error_signal.emit(RuntimeError(Translator.ERROR_MESSAGES("FFMPEG_NO_RESPONSE")), stdout, stderr)
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

    def _wait_proc(self, proc: subprocess.Popen, timeout: float = 10.0):
        """
        回收子进程，并对收尾阶段设一个上限

        走到这里时管道已经 EOF，正常情况下进程马上就会退出。若仍未退出，
        说明它卡在了最后的写操作上，此时只能强杀，否则本线程会一直等下去
        """
        try:
            return proc.wait(timeout = timeout)

        except subprocess.TimeoutExpired:
            logger.warning("FFmpeg 管道已关闭但进程仍未退出，强制结束")

            try:
                proc.kill()

            except OSError:
                # 进程可能刚好已经退出，忽略即可
                pass

            return proc.wait()

    def _start_watchdog(self, proc: subprocess.Popen):
        """
        监视 FFmpeg 的输出心跳，长时间毫无动静就终止它

        终止之后管道随即 EOF，_read_output 的两个读循环会自行收尾，
        与用户主动停止走的是同一条路径，无需额外的唤醒手段
        """
        def watch():
            while not self._watchdog_stop.wait(_WATCHDOG_INTERVAL):
                if proc.poll() is not None:
                    return

                if time.monotonic() - self._last_output_time < _NO_OUTPUT_TIMEOUT:
                    continue

                # 先置位再终止：run() 据此区分「无响应被杀」与「真的执行失败」
                self._watchdog_fired = True

                logger.error(f"FFmpeg 已有 {int(_NO_OUTPUT_TIMEOUT)} 秒没有任何输出，判定为无响应并终止")

                try:
                    proc.terminate()

                except OSError:
                    # 同上，进程可能已经退出
                    pass

                return

        thread = Thread(target = watch, name = "ffmpeg-watchdog", daemon = True)
        thread.start()

        return thread

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

                    self._last_output_time = time.monotonic()

                    stderr_lines.append(line)

                    self._parse_duration(line)

            except (OSError, ValueError):
                # 进程被终止时管道会提前关闭，读失败无需处理
                # （已关闭的文件对象抛 ValueError，底层读失败抛 OSError）
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

                self._last_output_time = time.monotonic()

                stdout_lines.append(line)

                self._parse_progress(line)

        except (OSError, ValueError):
            # 同上：进程被终止时 stdout 管道同样会提前关闭
            pass

        stderr_thread.join()

        for pipe in (proc.stdout, proc.stderr):
            try:
                pipe.close()

            except OSError:
                # 管道可能已随进程退出而失效，关闭失败无需处理
                pass

        return "".join(stdout_lines), "".join(stderr_lines)

    def _parse_duration(self, line: str):
        # 合并阶段有视频、音频、封面等多路输入，每一路都会打印自己的 Duration，
        # 封面这类图片输入的时长极短，取最长的那一路才是输出文件的实际时长
        for match in _DURATION_PATTERN.finditer(line):
            duration = self._to_seconds(match)

            # 只在「FFmpeg 自报」这一组内部取最大值，不与预设兜底值比较，
            # 否则一个被高估的预设值会让真实时长永远无法生效
            if duration > self._probed_duration:
                self._probed_duration = duration

    def _parse_progress(self, line: str):
        if not line.startswith(_PROGRESS_TIME_KEY):
            return

        value = line[len(_PROGRESS_TIME_KEY):].strip()

        # 还没有实际输出时这一项会是 N/A
        if not value.isdigit():
            return

        # _probed_duration 由读 stderr 的那个线程写入。属性读写在 GIL 下是原子的，
        # 这里只要一份能用的快照，偶尔读到旧值也只是少算一格进度。
        # FFmpeg 自报的时长一旦拿到就完全接管，预设值仅在它缺席时兜底
        duration = self._probed_duration or self._duration

        if duration <= 0:
            # concat 输入常被报成 Duration: N/A，上游也可能压根没给时长。
            # 此时百分比无从算起，界面只剩纯文案，看上去就像卡住了，
            # 这里留一条线索，便于事后从日志区分「没进度」和「真卡死」
            if not self._duration_warned:
                self._duration_warned = True

                logger.warning("未能获得媒体总时长，本次 FFmpeg 任务全程无法显示进度")

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

            except OSError:
                # 子进程可能刚好已经退出，此时 terminate 会失败，忽略即可
                pass

        return self.wait(timeout)
