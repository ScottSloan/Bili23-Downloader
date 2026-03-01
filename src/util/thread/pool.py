from PySide6.QtCore import QThreadPool, QRunnable

pool = QThreadPool.globalInstance()

class GlobalThreadPoolTask:
    @staticmethod
    def run(runnable: QRunnable):
        pool.start(runnable)
