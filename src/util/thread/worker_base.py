from PySide6.QtCore import Signal, QObject, Slot

class WorkerBase(QObject):
    success = Signal()
    error = Signal()
    finished = Signal()

    def __init__(self, parent = None):
        super().__init__(parent)

    @Slot()
    def run(self):
        pass
