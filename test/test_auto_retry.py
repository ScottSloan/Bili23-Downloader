"""
任务级自动重试的状态机（Issue #469）。

分片级重试（ChunkWorker.max_retries）解决的是单个分片的瞬时抖动；CDN 持续在几 KB
处掐断连接时，那 5 次配额会被一次性耗光，任务从此钉死在 FAILED，只能靠用户手动点。
补上的这一层是任务级重排队。

这里断言的是策略本身，因此刻意不驱动真实的事件循环，而是手工调用 _on_retry_tick()
逐秒推进 —— 倒计时依赖 QTimer 的 1 秒间隔，等真实时间流逝会让用例变慢且不稳定。

需要盯住的几条不变量：

1. 只有网络类可重试错误才进重试，403/404 这类永久错误必须一次就进终态；
2. 倒计时期间状态始终是 FAILED —— 并发调度器只认 QUEUED，状态一旦提前改掉，
   任务会绕开 download_parallel 的槽位控制被抢跑；
3. 暂停、删除、手动重试都要让还在跑的倒计时作废，绝不能把用户刚暂停的任务拉回队列。
"""

from PySide6.QtWidgets import QApplication

import pytest


@pytest.fixture(scope = "module")
def app():
    # QTimer 需要一个 QCoreApplication 才能构造，全进程复用同一个实例
    return QApplication.instance() or QApplication([])


@pytest.fixture
def restore_config():
    from util.common.config import config

    saved = {
        "enabled": config.get(config.auto_retry_enabled),
        "max_count": config.get(config.auto_retry_max_count),
    }

    yield config

    config.set(config.auto_retry_enabled, saved["enabled"])
    config.set(config.auto_retry_max_count, saved["max_count"])


@pytest.fixture
def downloader(app, restore_config, monkeypatch):
    from util.download.downloader.downloader import Downloader
    from util.download.task.info import TaskInfo
    from util.common.enum import DownloadStatus

    task_info = TaskInfo()
    task_info.Basic.task_id = "auto-retry-test"
    task_info.Download.status = DownloadStatus.DOWNLOADING

    instance = Downloader(task_info)

    # 落盘与并发调度不在本用例的关注范围内，切断即可：留着会在测试进程里拉起
    # 写线程与信号链路，用例断言的却只是内存中的状态机
    monkeypatch.setattr(instance, "update_item", lambda task_info: None)

    yield instance

    instance._retry_timer.stop()
    instance._close_session()


@pytest.fixture
def toasts():
    # 终态失败才该弹提示，倒计时期间不弹 —— 网络差的用户往往几十个任务一起失败
    from util.common.signal_bus import signal_bus

    emitted = []

    def record(*args):
        emitted.append(args)

    signal_bus.toast.show_long_message.connect(record)

    yield emitted

    signal_bus.toast.show_long_message.disconnect(record)


def _fail(downloader, retryable):
    # 每次失败都要先放开这个闸，否则 on_download_error 会在入口直接返回
    downloader._download_error_triggered = False

    downloader.on_download_error("peer closed connection", retryable)


class TestScheduling:
    def test_retryable_error_schedules_retry(self, downloader, toasts):
        from util.common.enum import DownloadStatus

        _fail(downloader, True)

        assert downloader._retry_pending
        assert downloader._retry_timer.isActive()
        assert downloader._auto_retry_count == 1
        # 倒计时期间必须停在 FAILED：改成别的状态会让并发调度器把它当成可跑的任务
        assert downloader.task_info.Download.status == DownloadStatus.FAILED
        assert downloader.task_info.Download.status_label
        assert not toasts, "安排了自动重试就不该再弹失败提示"

    def test_permanent_error_goes_terminal(self, downloader, toasts):
        _fail(downloader, False)

        assert not downloader._retry_pending
        assert downloader._auto_retry_count == 0
        assert not downloader.task_info.Download.status_label
        assert len(toasts) == 1, "不可重试的错误应当照旧提示用户"

    def test_disabled_by_config(self, downloader, restore_config, toasts):
        restore_config.set(restore_config.auto_retry_enabled, False)

        _fail(downloader, True)

        assert not downloader._retry_pending
        assert len(toasts) == 1

    def test_quota_exhausted_goes_terminal(self, downloader, restore_config, toasts):
        restore_config.set(restore_config.auto_retry_max_count, 2)

        _fail(downloader, True)
        _fail(downloader, True)

        assert downloader._auto_retry_count == 2
        assert downloader._retry_pending
        assert not toasts

        # 第三次没有配额了，转为终态并提示一次
        _fail(downloader, True)

        assert not downloader._retry_pending
        assert len(toasts) == 1

    def test_backoff_grows_and_caps(self, downloader, restore_config):
        restore_config.set(restore_config.auto_retry_max_count, 10)

        delays = []

        for _ in range(6):
            _fail(downloader, True)

            delays.append(downloader._retry_remaining)

        # 与分片级那套（秒级、封顶 8 秒）刻意拉开量级：间隔太短只是把同一个失败更密集地重放
        assert delays == [30, 60, 120, 240, 300, 300]

    def test_progress_resets_quota(self, downloader, restore_config):
        restore_config.set(restore_config.auto_retry_max_count, 3)

        _fail(downloader, True)
        _fail(downloader, True)

        assert downloader._auto_retry_count == 2

        # 这轮重试确有新数据落盘，说明网络只是时好时坏，不该继续消耗配额
        downloader.task_info.Download.downloaded_size = 4096

        _fail(downloader, True)

        assert downloader._auto_retry_count == 1, "有进展之后配额应当归零重数"

    def test_redownload_resets_quota(self, downloader, restore_config):
        restore_config.set(restore_config.auto_retry_max_count, 3)

        downloader.task_info.Download.downloaded_size = 4096

        _fail(downloader, True)
        _fail(downloader, True)

        assert downloader._auto_retry_count == 2

        # task_manager.reset() 会把已下载量清零（重新下载），此时 Downloader 实例可能还活着。
        # 只比较「是否变多」的话，基线停在旧的高位，这条任务就再也拿不回配额了
        downloader.task_info.Download.downloaded_size = 0

        _fail(downloader, True)

        assert downloader._auto_retry_count == 1, "重新下载之后配额应当归零重数"


class TestCountdown:
    def test_tick_requeues_when_countdown_ends(self, downloader, restore_config):
        from util.common.enum import DownloadStatus

        _fail(downloader, True)

        for _ in range(downloader._retry_remaining):
            downloader._on_retry_tick()

        assert downloader.task_info.Download.status == DownloadStatus.QUEUED
        assert not downloader._retry_pending
        assert not downloader._retry_timer.isActive()
        assert not downloader.task_info.Download.status_label

    def test_label_counts_down(self, downloader):
        _fail(downloader, True)

        before = downloader._retry_remaining

        downloader._on_retry_tick()

        assert downloader._retry_remaining == before - 1
        assert str(before - 1) in downloader.task_info.Download.status_label


class TestInvalidation:
    def test_pause_cancels_pending_retry(self, downloader):
        from util.common.enum import DownloadStatus

        _fail(downloader, True)

        downloader.pause()

        assert not downloader._retry_pending
        assert not downloader._retry_timer.isActive()
        assert downloader.task_info.Download.status == DownloadStatus.PAUSED

        # 即便有一次迟到的 tick 落进来，也不能把用户刚暂停的任务拉回队列
        downloader._on_retry_tick()

        assert downloader.task_info.Download.status == DownloadStatus.PAUSED

    def test_stale_generation_is_discarded(self, downloader):
        from util.common.enum import DownloadStatus

        _fail(downloader, True)

        # 模拟期间发生过暂停、删除一类会提升代次的操作
        downloader.download_generation += 1

        downloader._on_retry_tick()

        assert not downloader._retry_pending
        assert downloader.task_info.Download.status == DownloadStatus.FAILED

    def test_manual_retry_resets_quota(self, downloader, restore_config, monkeypatch):
        restore_config.set(restore_config.auto_retry_max_count, 2)

        monkeypatch.setattr(downloader, "start", lambda: None)

        _fail(downloader, True)
        _fail(downloader, True)

        assert downloader._auto_retry_count == 2

        # 用户手动介入，应当重新拿到一份完整配额
        downloader.retry()

        assert downloader._auto_retry_count == 0
