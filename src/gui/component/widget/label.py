from PySide6.QtGui import QColor, QMovie, QPixmap
from PySide6.QtWidgets import QLabel
from PySide6.QtCore import QSize, Qt

from qfluentwidgets import FluentLabelBase, getFont, CaptionLabel, isDarkTheme, BodyLabel, ImageLabel as _ImageLabel

from util.common.config import config

class SectionLabel(FluentLabelBase):
    """
    SectionLabel 用于显示分区标题，字体大小 16pt，介于 BodyLabel (14pt) 和 SubtitleLabel (20pt) 之间。
    """

    def getFont(self):
        return getFont(16)
    
class TipCaptionLabel(CaptionLabel):
    """
    TipCaptionLabel 用于显示提示信息，字体颜色为灰色。
    """

    def __init__(self, text = "", parent = None):
        super().__init__(parent)

        color = QColor(206, 206, 206) if isDarkTheme() else QColor(96, 96, 96)

        self.setStyleSheet('QLabel{color: ' + color.name() + '}')
        self.setText(text)

class TipBodyLabel(BodyLabel):
    """
    TipBodyLabel 用于显示提示信息，字体颜色为灰色。
    """

    def __init__(self, text = "", parent = None):
        super().__init__(parent)

        color = QColor(206, 206, 206) if isDarkTheme() else QColor(96, 96, 96)

        self.setStyleSheet('QLabel{color: ' + color.name() + '}')
        self.setText(text)

class TagLabel(QLabel):
    """
    TagLabel 用于显示圆角矩形的彩色标签，可指定主题色，配色随明暗主题自动切换。
    """

    def __init__(self, text = "", color: QColor = None, parent = None):
        super().__init__(parent)

        self._color = color if color else QColor("#0078D4")

        self.setFont(getFont(11))
        self.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.setFixedHeight(20)
        self.setText(text)

        config.themeChanged.connect(self.setTagQSS)

        self.setTagQSS()

    def setTagColor(self, color: QColor):
        self._color = color

        self.setTagQSS()

    def setTagQSS(self):
        r, g, b = self._color.red(), self._color.green(), self._color.blue()

        if isDarkTheme():
            # 深色主题下提亮文字颜色，并加深底色，保证在暗背景上的可读性
            text_color = self._color.lighter(150)
            background_alpha, border_alpha = 25, 50
        else:
            # 浅色主题下压暗文字颜色，避免亮色系标签的文字对比度不足
            text_color = self._color.darker(135)
            background_alpha, border_alpha = 12, 35

        self.setStyleSheet(
            "QLabel {"
            f"color: {text_color.name()};"
            f"background-color: rgba({r}, {g}, {b}, {background_alpha}%);"
            f"border: 1px solid rgba({r}, {g}, {b}, {border_alpha}%);"
            "border-radius: 10px;"
            "padding: 0px 8px 0px 8px;"
            "}"
        )

        self.adjustSize()

class ImageLabel(QLabel):
    def __init__(self, parent = None):
        super().__init__(parent)

    def loading(self):
        # 白色背景占位图
        placeholder_pixmap = QPixmap(self.size())
        placeholder_pixmap.fill(Qt.GlobalColor.white)
        
        self.setPixmap(placeholder_pixmap)

        # 播放加载动画
        self.loading_img = _ImageLabel(self)

        self.loading_movie = QMovie(":/bili23/icon/loading.gif")
        self.loading_img.setMovie(self.loading_movie)

        self._center_loading_img()

    def stop(self):
        self.loading_movie.stop()
        self.loading_img.hide()

    def _center_loading_img(self):
        dec_size = QSize(48, 48)

        x = (self.width() - dec_size.width()) // 2
        y = (self.height() - dec_size.height()) // 2

        self.loading_img.move(x, y)
