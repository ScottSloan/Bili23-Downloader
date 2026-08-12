from PySide6.QtWidgets import QStyledItemDelegate, QStyleOptionViewItem, QApplication, QStyle
from PySide6.QtGui import QPainter, QColor, QFont, QFontMetrics, QPixmap, QPainterPath
from PySide6.QtCore import QModelIndex, Qt, QRect, Signal, QPoint, QEvent

from qfluentwidgets import isDarkTheme, drawIcon, getFont, qconfig, ThemeColor, Theme, FluentIconBase

from typing import List
from collections import OrderedDict

# 绘制缓存。委托的 paint 在滚动时按 可见项 × 元素数 的量级重复调用，下列三项每次都要重新构造，
# 缓存后可显著降低单帧耗时（单帧耗时超过 16ms 会直接拖慢平滑滚动的动画推进）。
# 缓存键均包含主题或字体族信息，主题、字体变化后自然落到新的键上，无需主动清理。
_ICON_PIXMAP_CACHE: dict = {}
_FONT_CACHE: dict = {}
_ELIDED_TEXT_CACHE = OrderedDict()

# 省略文本的条目数上限，超出后按最近最少使用淘汰
_ELIDED_TEXT_CACHE_SIZE = 512

def _getCachedFont(fontSize: int):
    """按字体族与字号缓存 QFont 与 QFontMetrics

    getFont 每次都会新建 QFont 并从 qconfig 读取字体族，QFontMetrics 也要重新构造。
    """
    key = (fontSize, tuple(qconfig.get(qconfig.fontFamilies)))

    cached = _FONT_CACHE.get(key)

    if cached is None:
        font = getFont(fontSize)
        cached = (font, QFontMetrics(font), key)

        _FONT_CACHE[key] = cached

    return cached

def _getCachedElidedText(text: str, width: int, metrics: QFontMetrics, font_key: tuple):
    """缓存省略后的文本

    elidedText 需要逐字符测量文本宽度，而列表滚动时绝大多数文本与列宽都没有变化。
    """
    key = (font_key, width, text)

    if key in _ELIDED_TEXT_CACHE:
        _ELIDED_TEXT_CACHE.move_to_end(key)

        return _ELIDED_TEXT_CACHE[key]

    elided_text = metrics.elidedText(text, Qt.TextElideMode.ElideRight, width)

    _ELIDED_TEXT_CACHE[key] = elided_text

    if len(_ELIDED_TEXT_CACHE) > _ELIDED_TEXT_CACHE_SIZE:
        _ELIDED_TEXT_CACHE.popitem(last = False)

    return elided_text

class FluentStyledItemDelegate:
    def __init__(self):
        self.hoverRow = -1
        self.pressedRow = -1
        self.selectedRows = set()

    def setHoverRow(self, row: int):
        pass

    def setPressedRow(self, row: int):
        self.pressedRow = row

    def setSelectedRows(self, indexes: List[QModelIndex]):
        self.selectedRows.clear()

        for index in indexes:
            self.selectedRows.add(index.row())
            if index.row() == self.pressedRow:
                self.pressedRow = -1

    def _drawBackground(self, painter: QPainter, rect: QRect, index: QModelIndex):
        painter.setPen(Qt.PenStyle.NoPen)

        isHover = self.hoverRow == index.row()
        isPressed = self.pressedRow == index.row()
        isDark = isDarkTheme()

        c = 255 if isDark else 0
        alpha = 0

        if index.row() not in self.selectedRows:
            if isPressed:
                alpha = 9 if isDark else 6
            elif isHover:
                alpha = 12
        else:
            if isPressed:
                alpha = 15 if isDark else 9
            elif isHover:
                alpha = 25
            else:
                alpha = 17

        painter.setBrush(QColor(c, c, c, alpha))
        painter.drawRoundedRect(rect, 5, 5)

    def _drawPressedBackground(self, painter: QPainter, rect: QRect, index: QModelIndex):
        # 绘制可见的按下背景
        painter.setPen(Qt.PenStyle.NoPen)

        isDark = isDarkTheme()

        c = 255 if isDark else 0
        alpha = 15 if isDark else 9

        painter.setBrush(QColor(c, c, c, alpha))
        painter.drawRoundedRect(rect, 5, 5)

    def _drawPrimaryButton(self, painter: QPainter, rect: QRect, icon, hover = False):
        if hover:
            if isDarkTheme():
                primaryColor = ThemeColor.DARK_1.color()
            else:
                primaryColor = ThemeColor.LIGHT_1.color()
        else:
            primaryColor = ThemeColor.PRIMARY.color()

        borderColor = ThemeColor.LIGHT_1.color()

        # 主色按钮的底色较深，图标需要反色显示
        self._drawButtonBase(painter, rect, primaryColor, borderColor, icon, self._reverseTheme())

    def _drawButton(self, painter: QPainter, rect: QRect, icon, hover = False):
        if isDarkTheme():
            if hover:
                primaryColor = QColor(255, 255, 255, 21)
            else:
                primaryColor = QColor(255, 255, 255, 15)

            borderColor = QColor(255, 255, 255, 13)
        else:
            if hover:
                primaryColor = QColor(249, 249, 249, 128)
            else:
                primaryColor = QColor(255, 255, 255, 178)

            borderColor = QColor(255, 255, 255, 19)

        self._drawButtonBase(painter, rect, primaryColor, borderColor, icon)

    def _drawButtonBase(self, painter: QPainter, rect: QRect, primaryColor: QColor, borderColor: QColor, icon, theme = Theme.AUTO):
        painter.setPen(Qt.PenStyle.NoPen)

        # 绘制边框
        painter.setBrush(borderColor)
        painter.drawRoundedRect(rect, 5, 5)

        # 绘制背景
        painter.setBrush(primaryColor)
        painter.drawRoundedRect(rect.adjusted(1, 1, -1, -1), 5, 5)

        # 绘制图标
        self._drawCachedIcon(painter, rect.adjusted(8, 8, -8, -8), icon, theme)

    def _drawCachedIcon(self, painter: QPainter, rect: QRect, icon, theme = Theme.AUTO):
        """将图标渲染结果缓存为位图后再绘制

        FluentIcon 的 render 最终走 drawSvgIcon，每次调用都会新建 QSvgRenderer 重新解析 SVG，
        列表滚动时按 可见项 × 图标数 的量级重复解析。图标种类与尺寸都很有限，缓存位图后直接贴图。
        """
        device = painter.device()
        ratio = device.devicePixelRatioF() if device else 1.0

        key = (self._getIconKey(icon, theme), rect.width(), rect.height(), ratio)

        pixmap = _ICON_PIXMAP_CACHE.get(key)

        if pixmap is None:
            pixmap = QPixmap(round(rect.width() * ratio), round(rect.height() * ratio))
            pixmap.setDevicePixelRatio(ratio)
            pixmap.fill(Qt.GlobalColor.transparent)

            icon_painter = QPainter(pixmap)
            icon_painter.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)

            icon_rect = QRect(0, 0, rect.width(), rect.height())

            if isinstance(icon, FluentIconBase):
                icon.render(icon_painter, icon_rect, theme)
            else:
                drawIcon(icon, icon_painter, icon_rect)

            icon_painter.end()

            _ICON_PIXMAP_CACHE[key] = pixmap

        # 位图的逻辑尺寸与 rect 一致，按左上角贴图即可，无需再次缩放
        painter.drawPixmap(rect.topLeft(), pixmap)

    def _getIconKey(self, icon, theme):
        # FluentIcon 的资源路径本身已经区分主题，可直接作为缓存键
        if isinstance(icon, FluentIconBase):
            return icon.path(theme)

        return str(icon)

    def _drawProgressBar(self, painter: QPainter, rect: QRect, value: int, error = False, paused = False):
        if isDarkTheme():
            backgroundColor = QColor(255, 255, 255, 155)
        else:
            backgroundColor = QColor(0, 0, 0, 155)

        if error:
            barColor = QColor(255, 153, 164) if isDarkTheme() else QColor(196, 43, 28)
        elif paused:
            barColor = QColor(252, 225, 0) if isDarkTheme() else QColor(157, 93, 0)
        else:
            barColor = ThemeColor.PRIMARY.color()

        # 绘制背景
        painter.setPen(backgroundColor)
        painter.drawLine(rect.left(), rect.top(), rect.right(), rect.top())

        # 绘制进度
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(barColor)

        w = int(value / 100 * rect.width())
        r = rect.height() / 4

        painter.drawRoundedRect(rect.left(), rect.top() - 2, w, r, 1, 1)

    def _drawPixmap(self, painter: QPainter, rect: QRect, option: QStyleOptionViewItem, pixmap: QPixmap, isPlaceholder = False):
        if isPlaceholder:
            # 占位图背景
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(QColor(227, 229, 231))

            painter.drawRoundedRect(rect, 5, 5)

        else:
            # 绘制圆角图片
            path = QPainterPath()
            path.addRoundedRect(rect, 5, 5)

            painter.setClipPath(path)

        painter.drawPixmap(rect, pixmap)

        painter.setClipRect(option.rect)

    def _drawText(self, painter: QPainter, rect: QRect, text: str):
        if isDarkTheme():
            textColor = QColor(255, 255, 255)
        else:
            textColor = QColor(0, 0, 0)

        self._drawTextBase(painter, rect, text, textColor, 14)

    def _drawTextBase(self, painter: QPainter, rect: QRect, text: str, textColor: QColor, fontSize: int, textFlags = None):
        font, metrics, font_key = _getCachedFont(fontSize)

        elided_title = _getCachedElidedText(text, rect.width(), metrics, font_key)

        painter.setFont(font)
        painter.setPen(textColor)

        if textFlags:
            painter.drawText(rect, textFlags, elided_title)
        else:
            painter.drawText(rect, elided_title)

    def _drawDescriptionText(self, painter: QPainter, rect: QRect, text: str, error = False):
        if error:
            textColor = QColor(255, 153, 164) if isDarkTheme() else QColor(196, 43, 28)
        else:
            textColor = QColor(206, 206, 206) if isDarkTheme() else QColor(96, 96, 96)

        textFlags = Qt.TextFlag.TextWordWrap | Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter

        # 自动换行并左对齐、垂直居中
        self._drawTextBase(painter, rect, text, textColor, 14, textFlags)

    def _drawIndicator(self, painter: QPainter, rect: QRect, color: QColor):
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(color)

        painter.drawEllipse(rect)

    def _getFont(self, size: int):
        font = QApplication.font()
        font.setPointSize(size)
        font.setHintingPreference(QFont.HintingPreference.PreferNoHinting)

        return font

    def _reverseTheme(self):
        # 取与当前主题相反的主题，使图标在深色底上呈浅色、浅色底上呈深色
        return Theme.DARK if not isDarkTheme() else Theme.LIGHT

class ContextMenuDelegateBase(QStyledItemDelegate, FluentStyledItemDelegate):
    """
    具有右键菜单功能的委托基类
    """
    itemClicked = Signal(QModelIndex, object)
    contextMenuRequested = Signal(QModelIndex, QPoint)

    def __init__(self, parent = None):
        super().__init__(parent)

    def _checkHoverRow(self, option: QStyleOptionViewItem, index: QModelIndex):
        if option.state & QStyle.StateFlag.State_MouseOver:
            self.hoverRow = index.row()

        elif self.hoverRow == index.row():
            self.hoverRow = -1

    def editorEvent(self, event, model, option, index):
        if event.type() == QEvent.Type.MouseButtonRelease:
            return self._pressEvent(option, index, event)

        return super().editorEvent(event, model, option, index)

    def _pressEvent(self, option: QStyleOptionViewItem, index: QModelIndex, event):
        if event.button() == Qt.MouseButton.LeftButton:
            self.itemClicked.emit(index, index.data(Qt.ItemDataRole.UserRole))

            return True
        
        if event.button() == Qt.MouseButton.RightButton:
            # 右键点击，弹出上下文菜单
            self.contextMenuRequested.emit(index, event.globalPos())

            return True

        return False

class CoverQueryDelegateBase(ContextMenuDelegateBase):
    """
    具有异步封面显示功能的委托基类
    """
    def __init__(self, parent = None):
        super().__init__(parent)

    def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
        painter.save()
        painter.setRenderHints(QPainter.RenderHint.Antialiasing | QPainter.RenderHint.SmoothPixmapTransform)

        painter.setClipping(True)
        painter.setClipRect(option.rect)

        self._checkHoverRow(option, index)

        self._drawBackground(painter, option.rect, index)

        self._paintItemUI(painter, option, index)

        painter.restore()

    def _queryCover(self, cover_id: str, cover_url: str, index: QModelIndex):
        # 由委托发起查询封面请求
        return index.model().queryRowCover(cover_id, cover_url, index.row())
    
    def _drawCover(self, painter: QPainter, rect: QRect, option: QStyleOptionViewItem, index: QModelIndex, cover_id: str, cover_url: str):
        # 先绘制占位图
        pixmap, isPlaceholder = self._queryCover(cover_id, cover_url, index)

        self._drawPixmap(painter, rect, option, pixmap, isPlaceholder)
