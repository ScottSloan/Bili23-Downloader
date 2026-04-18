from PySide6.QtWidgets import QVBoxLayout, QSizePolicy
from PySide6.QtGui import QFontMetrics
from PySide6.QtCore import Qt

from qfluentwidgets import InfoBarIcon, InfoBarPosition, FluentIconBase, InfoBar as _InfoBar

from .scroll import ScrollArea

from typing import Union

class InfoBar(_InfoBar):
    def __init__(
        self,
        icon: Union[InfoBarIcon, FluentIconBase, str],
        title: str,
        content: str,
        orient = Qt.Orientation.Horizontal,
        isClosable = True,
        duration = 1000,
        position = InfoBarPosition.TOP_RIGHT,
        parent = None,
        contentMaxHeight = 120,
    ):
        super().__init__(icon, title, content, orient, isClosable, duration, position, parent)

        self.contentMaxHeight = contentMaxHeight

        self._contentContainerLayout = QVBoxLayout()
        self._contentContainerLayout.setContentsMargins(0, 0, 0, 0)
        self._contentContainerLayout.setSpacing(0)
        self._contentContainerLayout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._contentContainerLayout.addWidget(self.contentLabel)

        self.contentScrollArea = ScrollArea(self)
        self.contentScrollArea.setContentsMargins(0, 0, 0, 0)
        self.contentScrollArea.setObjectName('contentScrollArea')
        self.contentScrollArea.setScrollLayout(self._contentContainerLayout, resizable = False)

        self.textLayout.removeWidget(self.contentLabel)
        self.textLayout.insertWidget(1, self.contentScrollArea)

        self.contentLabel.setVisible(bool(content))
        self.contentScrollArea.setVisible(bool(content))

        self._adjustContentHeight()

    def _adjustText(self):
        self.titleLabel.setText(self.title)
        self.contentLabel.setText(self.content)

        metrics = QFontMetrics(self.contentLabel.font())
        lineWidths = self.content.splitlines() or [self.content]
        naturalWidth = max((metrics.horizontalAdvance(line) for line in lineWidths), default=0)

        self.contentLabel.setWordWrap(naturalWidth > 300)

        self.adjustSize()
        
        if hasattr(self, 'contentScrollArea'):
            self._adjustContentHeight()

    def _adjustContentHeight(self):
        if not hasattr(self, 'contentScrollArea'):
            return

        availableWidth = self.contentLabel.width()
        if availableWidth <= 0:
            availableWidth = self.contentScrollArea.viewport().width()
        if availableWidth <= 0:
            availableWidth = self.contentScrollArea.width()

        contentHeight = self.contentLabel.heightForWidth(availableWidth)

        self.contentScrollArea.setFixedHeight(min(contentHeight, self.contentMaxHeight))
        self.contentScrollArea.setVisible(bool(self.content))
        
    @classmethod
    def new(
        cls,
        icon,
        title,
        content,
        orient = Qt.Orientation.Horizontal,
        isClosable = True,
        duration = 1000,
        position = InfoBarPosition.TOP_RIGHT,
        parent = None,
        contentMaxHeight = 120,
    ):
        w = cls(icon, title, content, orient, isClosable, duration, position, parent, contentMaxHeight)
        w.show()
        return w

    @classmethod
    def info(
        cls,
        title,
        content,
        orient = Qt.Orientation.Horizontal,
        isClosable = True,
        duration = 1000,
        position = InfoBarPosition.TOP_RIGHT,
        parent = None,
        contentMaxHeight = 120,
    ):
        return cls.new(InfoBarIcon.INFORMATION, title, content, orient, isClosable, duration, position, parent, contentMaxHeight)

    @classmethod
    def success(
        cls,
        title,
        content,
        orient = Qt.Orientation.Horizontal,
        isClosable = True,
        duration = 1000,
        position = InfoBarPosition.TOP_RIGHT,
        parent = None,
        contentMaxHeight = 120,
    ):
        return cls.new(InfoBarIcon.SUCCESS, title, content, orient, isClosable, duration, position, parent, contentMaxHeight)

    @classmethod
    def warning(
        cls,
        title,
        content,
        orient = Qt.Orientation.Horizontal,
        isClosable = True,
        duration = 1000,
        position = InfoBarPosition.TOP_RIGHT,
        parent = None,
        contentMaxHeight = 120,
    ):
        return cls.new(InfoBarIcon.WARNING, title, content, orient, isClosable, duration, position, parent, contentMaxHeight)

    @classmethod
    def error(
        cls,
        title,
        content,
        orient = Qt.Orientation.Horizontal,
        isClosable = True,
        duration = 1000,
        position = InfoBarPosition.TOP_RIGHT,
        parent = None,
        contentMaxHeight = 120,
    ):
        return cls.new(InfoBarIcon.ERROR, title, content, orient, isClosable, duration, position, parent, contentMaxHeight)
