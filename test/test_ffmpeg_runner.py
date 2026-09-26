"""
util/ffmpeg/runner.py —— 合并阶段的进度换算与无响应保护。

这两件事都对应线上一个具体的现象：任务进入合并阶段后显示「合并中...」，
不带百分比，且长时间不动。它由两个互相独立的原因叠加而成，各自单独发生时
症状完全一样，从界面上分不出来，所以两边都要钉住：

1. 进度算不出来（看起来卡住）
   进度条要的百分比 = 已处理时长 / 总时长。总时长有两个来源：调用方预设的
   Episode.duration（兜底），以及 FFmpeg 自己在 stderr 上报的 Duration。
   原实现把两者混在一起取最大值，于是一个被高估的预设值（上游各接口的
   duration 单位并不统一，部分是毫秒）会让真实时长永远无法生效，
   百分比全程算成 0，界面只剩纯文案。

2. FFmpeg 真的卡死（确实卡住）
   读管道和 wait 都是无限等待，FFmpeg 一旦卡在某次系统调用上（输出文件被
   外部程序占用、目标盘不可用），线程永不退出，任务永远停在 MERGING。
   而合并额度全局只有一个，这一个僵住会让整条下载队列再也排不下去。

因此这里分别验证：自报时长必须能覆盖预设值，以及无输出的进程必须被终止。
"""

from util.ffmpeg import runner as runner_module
from util.ffmpeg.runner import FFmpegRunner

import subprocess
import time
import sys

import pytest


@pytest.fixture
def runner():
    # 这里只驱动解析与看门狗，两者都不进事件循环，因此不构造 Q(Core)Application：
    # 进程里一旦先有了 QCoreApplication，之后需要 QApplication 的 GUI 测试就无法再创建
    return FFmpegRunner(["ffmpeg"])


def feed_stderr(runner: FFmpegRunner, *durations: str):
    for value in durations:
        runner._parse_duration(f"  Duration: {value}, start: 0.000000, bitrate: 1234 kb/s\n")


def collect_progress(runner: FFmpegRunner):
    received = []

    runner.progress_signal.connect(received.append)

    return received


class TestDurationResolution:
    def test_probed_duration_overrides_inflated_preset(self, runner):
        # 预设值被放大 1000 倍（毫秒当成秒），FFmpeg 报的真实时长是 100 秒。
        # 取最大值的老写法会一直用 100000，进度全程为 0
        runner.set_duration(100_000)
        feed_stderr(runner, "00:01:40.00")

        received = collect_progress(runner)
        runner._parse_progress("out_time_us=50000000\n")

        assert received == [50]

    def test_preset_is_used_until_ffmpeg_reports(self, runner):
        # FFmpeg 打印输入信息之前没有自报时长可用，此时预设值必须顶上，
        # 否则合并一开始的那几秒没有任何进度
        runner.set_duration(100)

        received = collect_progress(runner)
        runner._parse_progress("out_time_us=25000000\n")

        assert received == [25]

    def test_longest_reported_input_wins(self, runner):
        # 合并有视频、音频、封面等多路输入，每一路都会打印自己的 Duration。
        # 封面这类图片输入时长极短，取最长的那一路才是输出文件的实际时长
        feed_stderr(runner, "00:00:00.04", "00:01:40.00", "00:00:00.04")

        received = collect_progress(runner)
        runner._parse_progress("out_time_us=50000000\n")

        assert received == [50]

    def test_unknown_duration_emits_nothing(self, runner):
        # concat 输入常被报成 Duration: N/A，上游也可能压根没给时长。
        # 此时百分比无从算起，但绝不能因此抛异常把合并流程带崩
        runner._parse_duration("  Duration: N/A, start: 0.000000, bitrate: N/A\n")

        received = collect_progress(runner)
        runner._parse_progress("out_time_us=50000000\n")

        assert received == []

    def test_progress_is_capped_below_100(self, runner):
        # 留出最后 1%：收尾还有重命名、删除中间文件等步骤，
        # 先到 100% 再干等一会儿反而更像卡住
        runner.set_duration(100)

        received = collect_progress(runner)
        runner._parse_progress("out_time_us=100000000\n")

        assert received == [99]

    def test_na_progress_value_is_ignored(self, runner):
        # 还没有实际输出时 -progress 会把这一项写成 N/A
        runner.set_duration(100)

        received = collect_progress(runner)
        runner._parse_progress("out_time_us=N/A\n")

        assert received == []


class TestWatchdog:
    @pytest.fixture(autouse = True)
    def shorten_timeouts(self, monkeypatch):
        # 线上阈值是 5 分钟，测试里缩到秒级
        monkeypatch.setattr(runner_module, "_NO_OUTPUT_TIMEOUT", 0.5)
        monkeypatch.setattr(runner_module, "_WATCHDOG_INTERVAL", 0.1)

    def spawn(self, code: str):
        # 看门狗只看 poll() 和 terminate()，不读管道，
        # 这里用 DEVNULL 省掉测试自己收拾管道的负担
        return subprocess.Popen(
            [sys.executable, "-c", code],
            stdout = subprocess.DEVNULL,
            stderr = subprocess.DEVNULL,
        )

    def spawn_silent(self):
        # 一个只睡觉、不产生任何输出的子进程，用来模拟卡死的 FFmpeg
        return self.spawn("import time; time.sleep(30)")

    def test_silent_process_is_terminated(self, runner):
        proc = self.spawn_silent()

        try:
            runner._last_output_time = time.monotonic()
            watchdog = runner._start_watchdog(proc)

            assert proc.wait(timeout = 10) is not None
            assert runner._watchdog_fired is True

            watchdog.join(timeout = 5)
            assert not watchdog.is_alive()

        finally:
            if proc.poll() is None:
                proc.kill()

            proc.wait()

    def test_heartbeat_keeps_process_alive(self, runner):
        proc = self.spawn_silent()

        try:
            runner._last_output_time = time.monotonic()
            watchdog = runner._start_watchdog(proc)

            # 持续有输出就一直不该被动，这是看门狗不能误杀慢速合并的底线
            deadline = time.monotonic() + 1.5

            while time.monotonic() < deadline:
                runner._last_output_time = time.monotonic()
                time.sleep(0.05)

            assert runner._watchdog_fired is False
            assert proc.poll() is None

            runner._watchdog_stop.set()
            watchdog.join(timeout = 5)

        finally:
            proc.kill()
            proc.wait()

    def test_watchdog_exits_when_process_ends(self, runner):
        # 进程正常结束后看门狗必须自行退出，否则每跑一次合并就漏一个线程
        proc = self.spawn("pass")
        proc.wait()

        runner._last_output_time = time.monotonic()
        watchdog = runner._start_watchdog(proc)

        watchdog.join(timeout = 5)

        assert not watchdog.is_alive()
        assert runner._watchdog_fired is False
