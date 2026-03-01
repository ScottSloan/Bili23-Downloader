from util.thread.worker_base import WorkerBase

class SyncTask:
    @staticmethod
    def run(worker: WorkerBase):
        worker.finished.connect(worker.deleteLater)

        worker.run()
