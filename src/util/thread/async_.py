from PySide6.QtCore import QThread

from .worker_base import WorkerBase

from functools import partial
import logging
import time

logger = logging.getLogger(__name__)

thread_queue: list[tuple[QThread, WorkerBase]] = []

def remove_from_queue(thread: QThread, worker: WorkerBase):
    try:
        thread_queue.remove((thread, worker))

    except Exception:
        pass

    finally:
        try:
            thread.deleteLater()

        except RuntimeError:
            # 线程结束时本就会走一次 remove_from_queue，退出流程里可能再走一次，
            # 此时 C++ 对象可能已经销毁，忽略即可
            pass

class AsyncTask:
    @staticmethod
    def run(worker: WorkerBase, on_started = None, on_finished = None):
        thread = QThread()

        worker.moveToThread(thread)

        thread.started.connect(worker.run)

        if on_started:
            thread.started.connect(on_started)

        if on_finished:
            thread.finished.connect(on_finished)

        worker.finished.connect(thread.quit)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(partial(remove_from_queue, thread, worker))

        thread_queue.append((thread, worker))

        thread.start()
    
    @staticmethod
    def safe_quit(timeout: int = 3000):
        # timeout 是所有线程共享的总预算，而不是每个线程各等一次，
        # 否则线程一多，退出过程会被逐个等待拖得很久
        running = [(thread, worker) for thread, worker in list(thread_queue) if thread.isRunning()]

        if not running:
            return

        # 先统一发出退出请求再统一等待，避免预算全耗在第一个线程上
        for thread, _ in running:
            thread.quit()

        deadline = time.monotonic() + timeout / 1000

        for thread, worker in running:
            remaining = int((deadline - time.monotonic()) * 1000)

            if remaining > 0 and thread.wait(remaining):
                remove_from_queue(thread, worker)

                continue

            # 线程没能在预算内退出，通常是卡在一个还没超时的网络请求上（读超时 5s）。
            # 这里既不强杀也不销毁对象：
            #   - terminate() 在 Windows 上就是 TerminateThread，会在任意指令处杀死线程，
            #     若当时正持有 CRT 堆锁，之后任何一次 free 都可能触发 FAST_FAIL；
            #     而 safe_quit() 恰好排在退出前的数据库写入之前，是风险最高的位置。
            #   - deleteLater() 或从 thread_queue 摘除，都会销毁仍在运行的 QThread，
            #     直接触发 "QThread: Destroyed while thread is still running"。
            # 进程马上就要退出了，留着它随进程一起消失是最安全的做法。
            logger.warning("线程未能在 %d ms 内退出，已跳过强制终止：%s", timeout, type(worker).__name__)
