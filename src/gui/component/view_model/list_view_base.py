from PySide6.QtGui import QPainter, QColor, QFontMetrics

from qfluentwidgets import ListView, Action, isDarkTheme, setFont

class ContextMenuListViewBase(ListView):
    def __init__(self, parent = None):
        super().__init__(parent)

        self._emptyTextTip = ""

    def _create_action(self, icon, text, slot):
        action = Action(icon = icon, text = text, parent = self)
        action.triggered.connect(slot)
        
        return action
    
    def isEmpty(self):
        return self._model.rowCount() == 0
    
    def paintEvent(self, e):
        if self.isEmpty():
            if isDarkTheme():
                textColor = QColor(255, 255, 255)
            else:
                textColor = QColor(0, 0, 0)

            painter = QPainter(self.viewport())

            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            painter.setPen(textColor)
            
            setFont(painter, 14)

            fm = QFontMetrics(self.font())
            text_width = fm.horizontalAdvance(self._emptyTextTip)
            text_height = fm.height()

            x = (self.viewport().width() - text_width) // 2
            y = (self.viewport().height() + text_height) // 2

            painter.drawText(x, y, self._emptyTextTip)

        else:
            super().paintEvent(e)
