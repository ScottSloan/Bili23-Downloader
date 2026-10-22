from PySide6.QtWidgets import QWidget

from qfluentwidgets import Flyout as _Flyout

class Flyout(_Flyout):
    """
    弹出时不抢走主窗口激活状态的 Flyout

    qfluentwidgets 的 Flyout 在 showEvent 里无条件 activateWindow()（注释为 fixes #780），
    Windows 上激活随即从主窗口转到弹窗，主窗口标题栏立刻变成失焦样式，弹窗一关又切回来，
    每开一次浮窗整个窗口闪一下。

    Flyout 本身是 Qt.Popup，用不着系统激活：Qt 处于弹出模式时会把键盘事件转给弹窗里的
    焦点控件（QMenu、QComboBox 下拉都是这样工作的），浮窗里的输入框照样能打字。
    只有父窗口本来就没激活时（例如从托盘唤起）才沿用原来的 activateWindow()，
    那种情况下系统不会把键盘输入交给本进程
    """
    def showEvent(self, e):
        parent = self.parentWidget()

        if parent is None or not parent.window().isActiveWindow():
            self.activateWindow()

        # 越过 qfluentwidgets 的 showEvent，那里只做了无条件的 activateWindow()
        QWidget.showEvent(self, e)
