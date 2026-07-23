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
    #         # 在column 0末尾绘制图标按钮
    #         if index.column() == 0:
    #             rect = self.uiRect.getEpisodeSelectionRect(option)

    #             self._drawButton(painter, rect, FluentIcon.SEARCH)

class UIRect:
    def __init__(self):
        self.margin = 10
        self.spacer = 20

    def getEpisodeSelectionRect(self, option: QStyleOptionViewItem):
        # left 应是 column 0的右边界 + margin
        left = option.rect.left() + 100
        top = option.rect.top()

        return QRect(left, top, 28, 28)

