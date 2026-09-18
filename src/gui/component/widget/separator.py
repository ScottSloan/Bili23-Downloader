from PySide6.QtWidgets import QWidget, QSizePolicy
from PySide6.QtGui import QColor, QPainter, QPen

from qfluentwidgets import isDarkTheme

from util.common.config import config

class Separator(QWidget):
    """
    竖直分割线：宽度固定，高度随布局自动拉伸。

    基类必须能长高，这是这个控件唯一容易踩的地方。它原先继承 NavigationWidget，
    而 NavigationWidget 在 __init__ 里调了 setFixedSize(40, 36) —— 高度上界被钉死
    在 36px，后面那句 setFixedWidth(5) 只解开宽度。于是扔进 QHBoxLayout 也不会跟着
    布局长高，只能由调用方自己算好高度再 setFixedHeight()，flyout 里就留了这么一处
    补偿；rule_list 没补，那条线便一直只有 36px。改继承 QWidget 后上界不再受限。

    竖直方向声明成 Expanding 不是保险，是必需：高度不由 sizeHint 决定，而是靠这条
    策略从布局领到整行高度。放进 QGridLayout 时尤其明显 —— 没有它，sizeHint 高度为
    0 的控件会被压成一条看不见的线。
    """

    LINE_WIDTH = 5

    def __init__(self, parent = None, alpha: int = 25):
        """
        alpha 是线的不透明度，取值 0-255。线色在浅色主题下为黑、深色主题下为白，
        alpha 决定它融进背景的程度：25 用于面板内部分隔，50 用于按钮组之间。
        """
        super().__init__(parent)

        self._alpha = alpha

        self.setFixedWidth(self.LINE_WIDTH)
        self.setSizePolicy(QSizePolicy.Policy.Fixed, QSizePolicy.Policy.Expanding)

        # 线色取自 isDarkTheme()，主题切换后不重画就会一直留着上一个主题的颜色
        config.themeChanged.connect(self.update)

    def paintEvent(self, e):
        painter = QPainter(self)

        c = 255 if isDarkTheme() else 0

        pen = QPen(QColor(c, c, c, self._alpha))
        pen.setCosmetic(True)       # 高 DPI 下不跟着缩放变粗，始终是 1 物理像素

        painter.setPen(pen)

        # 按实际宽度取中点，不写死坐标：改 LINE_WIDTH 后线仍然居中
        x = self.width() // 2

        painter.drawLine(x, 0, x, self.height())
