from PySide6.QtCore import QThread

from functools import partial

from util.thread.worker_base import WorkerBase

thread_queue: list[tuple[QThread, WorkerBase]] = []

def remove_from_queue(thread: QThread, worker: WorkerBase):
    try:
        thread_queue.remove((thread, worker))

    except Exception:
        pass

    finally:
        thread.deleteLater()

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
    def safe_quit():
        for thread, worker in list(thread_queue):
            if thread.isRunning():
                thread.quit()
                thread.wait(deadline = 1000)

                remove_from_queue(thread, worker)
