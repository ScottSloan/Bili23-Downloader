from qfluentwidgets import SpinBox as _SpinBox, DoubleSpinBox as _DoubleSpinBox, CompactSpinBox as _CompactSpinbox

class SpinBox(_SpinBox):
    def __init__(self, ignore_wheel = False, parent = None):
        super().__init__(parent)

        self.ignore_wheel = ignore_wheel

    def wheelEvent(self, event):
        if self.ignore_wheel:
            event.ignore()

        else:
            return super().wheelEvent(event)
        
class DoubleSpinBox(_DoubleSpinBox):
    def __init__(self, ignore_wheel = False, parent = None):
        super().__init__(parent)

        self.ignore_wheel = ignore_wheel

    def wheelEvent(self, event):
        if self.ignore_wheel:
            event.ignore()

        else:
            return super().wheelEvent(event)
        
class CompactSpinBox(_CompactSpinbox):
    def __init__(self, ignore_wheel = False, parent = None):
        super().__init__(parent)

        self.ignore_wheel = ignore_wheel

    def wheelEvent(self, event):
        if self.ignore_wheel:
            event.ignore()

        else:
            return super().wheelEvent(event)
