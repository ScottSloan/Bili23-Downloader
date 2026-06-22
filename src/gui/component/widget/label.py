from PySide6.QtGui import QColor, QMovie, QPixmap
from PySide6.QtWidgets import QLabel
from PySide6.QtCore import QSize, Qt

from qfluentwidgets import FluentLabelBase, getFont, CaptionLabel, isDarkTheme, ImageLabel as _ImageLabel

class SectionLabel(FluentLabelBase):
    """
    SectionLabel 用于显示分区标题，字体大小 16pt，介于 BodyLabel (14pt) 和 SubtitleLabel (20pt) 之间。
    """

    def getFont(self):
        return getFont(16)
    
class TipLabel(CaptionLabel):
    """
    TipLabel 用于显示提示信息，字体颜色为灰色。
    """

    def __init__(self, text = "", parent = None):
        super().__init__(parent)

        color = QColor(206, 206, 206) if isDarkTheme() else QColor(96, 96, 96)

        self.setStyleSheet('QLabel{color: ' + color.name() + '}')
        self.setText(text)

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
