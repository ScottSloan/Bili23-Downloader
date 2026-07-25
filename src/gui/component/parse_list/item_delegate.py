from PySide6.QtWidgets import QStyleOptionViewItem, QStyle
from PySide6.QtCore import QModelIndex, QRect, Qt
from PySide6.QtGui import QPainter

from qfluentwidgets import TreeItemDelegate, FluentIcon

from gui.component.view_model.delegate_base import FluentStyledItemDelegate

class ParseTreeItemDelegate(TreeItemDelegate, FluentStyledItemDelegate):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.uiRect = UIRect()

    # def paint(self, painter: QPainter, option: QStyleOptionViewItem, index: QModelIndex):
    #     # 先调用父类的paint方法绘制基础的树形项
    #     super().paint(painter, option, index)

    #     # 根据鼠标焦点状态绘制独立的工具按钮
    #     if option.state & QStyle.StateFlag.State_MouseOver:
    #         # 默认在最后一个column上绘制图标按钮

    #         column_count = index.model().columnCount()

    #         if index.column() == column_count - 1:
    #             #取背景色，遮住原本的内容，绘制按钮
    #             painter.save()

    #             painter.setBrush()
    #             painter.setPen(Qt.PenStyle.NoPen)

    #             print(painter.brush().color())

    #             painter.restore()

    #             # 此处rect是最后一个column的rect，绘制按钮时需要根据实际需求调整位置和大小
    #             search_rect = self.uiRect.getSearchRect(option)
    #             download_rect = self.uiRect.getDownloadRect(search_rect)

    #             self._drawButton(painter, search_rect, FluentIcon.SEARCH)
    #             self._drawButton(painter, download_rect, FluentIcon.DOWNLOAD)

class UIRect:
    def __init__(self):
        self.margin = 10
        self.spacer = 20

        self.command_bar_width = 28 * 3 + 5 * 3

    def getSearchRect(self, option: QStyleOptionViewItem):
        # left 应是最后一个column的rect的左边界加上一定的偏移量，top 应是最后一个column的rect的上边界

        left = option.rect.left() + option.rect.width() - self.command_bar_width
        top = option.rect.top() + (option.rect.height() - 28) // 2

        return QRect(left, top, 28, 28)

    def getDownloadRect(self, search_rect: QRect):
        left = search_rect.left() + search_rect.width() + 28 + 5
        top = search_rect.top()

        return QRect(left, top, 28, 28)