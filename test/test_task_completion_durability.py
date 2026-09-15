"""
任务完成时的落盘保证。

Merger.mark_as_completed() 发出 remove_from_downloading_list 之后，会一路同步走到
Downloader.on_delete()，那是整个下载流程中最容易出现原生崩溃的一段（线程池与定时器
的销毁）。若这条记录还排在写线程的队列里，进程一旦没了它就永远丢了 —— 磁盘上躺着
合并好的成品文件，库里却停在「下载中」，重启后任务显示未完成，重复下载判定也失效。

因此 mark_as_completed(wait = True) 必须在返回前确保记录已经落库。这里断言的正是
「调用返回时表已经改完」，用例中刻意不做任何等待或重试 —— 一旦退回异步，断言立刻失败。
"""

from concurrent.futures import Future
from threading import Event

import pytest


@pytest.fixture
def task_manager():
    # conftest 已把 AppDataLocation 重定向到 qttest，这里建的库在隔离目录下
    from util.download.task.manager import TaskManager

    manager = TaskManager()

    yield manager

    # 连接是线程本地的，各线程只能关自己那一个：写线程的连接必须投递回写线程去关，
    # 否则线程退出后连接对象由 GC 回收，pytest 会报 unclosed database
    manager._update_executor.submit(manager.db_manager.close_connection)

    manager._update_executor.shutdown(wait = True)
    manager._cancel_executor.shutdown(wait = True)

    manager.db_manager.close_connection()


def _make_task(task_id: str):
    from util.common.enum import DownloadStatus
    from util.download.task.info import TaskInfo

    task_info = TaskInfo()
    task_info.Basic.task_id = task_id
    task_info.Basic.show_title = f"标题 {task_id}"
    task_info.Basic.created_time = 1_700_000_000
    task_info.Download.status = DownloadStatus.DOWNLOADING

    return task_info


def _task_ids(manager, completed: bool):
    table = "completed_task" if completed else "download_task"

    return {row[0] for row in manager.db_manager.query(f"SELECT task_id FROM {table}")}


class TestMarkAsCompletedDurability:
    def test_wait_true_is_on_disk_when_it_returns(self, task_manager):
        task_info = _make_task("wait-true")

        task_manager.db_manager.add_tasks([task_info])

        assert "wait-true" in _task_ids(task_manager, completed = False)

        task_manager.mark_as_completed(task_info, wait = True)

        # 关键断言：不 sleep、不重试。返回即已落库
        assert "wait-true" in _task_ids(task_manager, completed = True)
        assert "wait-true" not in _task_ids(task_manager, completed = False)

    def test_wait_true_does_not_deadlock_from_the_caller_thread(self, task_manager):
        # 调用方是 GUI 线程，等的是写线程。写线程只做数据库操作，其中的 emit 是跨线程
        # 排队、不会回等调用方，因此不存在互相等待。这里用一个超时兜住：真要死锁，
        # 用例会挂在这一行而不是悄悄通过
        task_info = _make_task("no-deadlock")

        task_manager.db_manager.add_tasks([task_info])

        done = Future()

        def run():
            task_manager.mark_as_completed(task_info, wait = True)
            done.set_result(True)

        from threading import Thread

        thread = Thread(target = run, daemon = True)
        thread.start()
        thread.join(timeout = 10)

        assert not thread.is_alive(), "mark_as_completed(wait = True) 未能在 10 秒内返回，疑似死锁"
        assert done.result(timeout = 1) is True

    def test_timeout_does_not_raise_and_write_still_lands(self, task_manager, caplog):
        # 写线程是单线程 FIFO，前面塞一个长任务就能逼出超时路径。
        # 超时只该记日志并放行，绝不能把异常抛回调用方 —— 抛出去就会中断
        # Merger.mark_as_completed，任务连界面上的完成状态都拿不到
        task_info = _make_task("timeout")

        task_manager.db_manager.add_tasks([task_info])

        release = Event()

        task_manager._update_executor.submit(release.wait)

        try:
            with caplog.at_level("ERROR"):
                task_manager.mark_as_completed(task_info, wait = True, timeout = 0.2)

            assert any("超时" in record.message for record in caplog.records)

        finally:
            release.set()

        # 超时只是放弃等待，写入本身仍在写线程上排队，最终必须落库
        task_manager._update_executor.submit(lambda: None).result(timeout = 10)

        assert "timeout" in _task_ids(task_manager, completed = True)

    def test_without_wait_there_is_no_durability_guarantee(self, task_manager):
        """
        反向验证：不等待时记录确实可能还没落库

        没有这条，上面那个「返回即已落库」的断言可能只是碰巧跑赢了写线程，
        看不出 wait 到底有没有生效。这里先把写线程堵死，再走一次默认路径，
        此刻库里必然还是旧状态 —— 崩溃发生在这个窗口里，记录就丢了
        """
        task_info = _make_task("no-guarantee")

        task_manager.db_manager.add_tasks([task_info])

        release = Event()

        task_manager._update_executor.submit(release.wait)

        try:
            task_manager.mark_as_completed(task_info)

            assert "no-guarantee" not in _task_ids(task_manager, completed = True)
            assert "no-guarantee" in _task_ids(task_manager, completed = False)

        finally:
            release.set()

        task_manager._update_executor.submit(lambda: None).result(timeout = 10)

        assert "no-guarantee" in _task_ids(task_manager, completed = True)

    def test_wait_false_keeps_the_old_asynchronous_contract(self, task_manager):
        # 默认参数不改变既有行为：仍是投递后立即返回，不阻塞调用方
        task_info = _make_task("wait-false")

        task_manager.db_manager.add_tasks([task_info])

        task_manager.mark_as_completed(task_info)

        # 这里必须等一下再断言 —— 异步路径不保证返回时已落库
        task_manager._update_executor.submit(lambda: None).result(timeout = 10)

        assert "wait-false" in _task_ids(task_manager, completed = True)
