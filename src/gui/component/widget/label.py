from PySide6.QtGui import QColor

from qfluentwidgets import FluentLabelBase, getFont, CaptionLabel, isDarkTheme

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
