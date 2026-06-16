from PySide6.QtGui import QColor, QMovie
from PySide6.QtCore import QSize

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

class ImageLabel(_ImageLabel):
    def __init__(self, parent = None):
        super().__init__(parent)

    def loading(self):
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
