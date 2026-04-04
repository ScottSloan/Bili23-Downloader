from PySide6.QtWidgets import QVBoxLayout, QWidget, QHBoxLayout, QStackedWidget, QListWidgetItem
from PySide6.QtGui import QColor, QIcon, QPainter, QPen
from PySide6.QtCore import Signal, Qt, QSize

from qfluentwidgets import (
    FlyoutViewBase, FluentIcon, isDarkTheme, ListWidget
)
from qfluentwidgets.components.navigation import NavigationWidget

from util.common import ExtendedFluentIcon, config, signal_bus

from typing import Union

class Separator(NavigationWidget):
    def __init__(self, parent = None):
        super().__init__(False, parent=parent)

        self.setFixedSize(5, 300)

        self.update()

    def paintEvent(self, e):
        painter = QPainter(self)

        c = 255 if isDarkTheme() else 0

        pen = QPen(QColor(c, c, c, 15))
        pen.setCosmetic(True)

        painter.setPen(pen)

        painter.drawLine(2, 0, 2, self.height())

class CategoryWidget(QWidget):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.init_UI()

        self.init_category_list()

    def init_UI(self):
        self.category_list = ListWidget(self)
        self.category_list.setMaximumWidth(175)

        viewLayout = QVBoxLayout(self)
        viewLayout.setContentsMargins(0, 0, 5, 0)

        viewLayout.addWidget(self.category_list)

    def init_category_list(self):
        category_list = [
            {
                "icon": ExtendedFluentIcon.FAVORITE,
                "text": self.tr("收藏夹"),
                "data": {
                    "isSelectable": True,
                }
            },
            {
                "icon": ExtendedFluentIcon.ALBUM,
                "text": self.tr("订阅合集"),
                "data": {
                    "isSelectable": True,
                }
            },
            {
                "icon": FluentIcon.HEART,
                "text": self.tr("追番追剧"),
                "data": {
                    "isSelectable": True,
                }
            },
            {
                "icon": ExtendedFluentIcon.CLOCK,
                "text": self.tr("稍后再看"),
                "data": {
                    "isSelectable": False,
                    "url": "bili23://watch_later"
                }
            },
            {
                "icon": FluentIcon.HISTORY,
                "text": self.tr("历史记录"),
                "data": {
                    "isSelectable": False,
                    "url": "bili23://history"
                }
            }
        ]

        for category in category_list:
            self.add_category(category["icon"], category["text"], category["data"])

        self.category_list.setCurrentRow(0)

        self.category_list.itemClicked.connect(self.on_list_item_clicked)

    def add_category(self, icon: Union[str, QIcon, FluentIcon], text: str, data: dict):
        item = QListWidgetItem(f"   {text}", self.category_list)
        item.setIcon(icon.icon())
        item.setData(Qt.ItemDataRole.UserRole, data)
        item.setSizeHint(QSize(0, 40))

        self.category_list.addItem(item)

    def on_list_item_clicked(self, item: QListWidgetItem):
        data = item.data(Qt.ItemDataRole.UserRole)

        parent_widget: 'FavoriteFlyoutMenu' = self.parent()

        if data["isSelectable"]:
            parent_widget.on_category_changed(self.category_list.row(item))
        
        else:
            parent_widget.closed.emit()
            
            signal_bus.parse.parse_url.emit(data["url"])

class LinkWidget(QWidget):
    def __init__(self, parent: 'FavoriteFlyoutMenu'):
        super().__init__(parent)

        self.parent_widget = parent

        self.init_UI()

    def init_UI(self):
        self.link_list = ListWidget(self)
        self.link_list.setFixedWidth(300)

        viewLayout = QVBoxLayout(self)
        viewLayout.setContentsMargins(5, 0, 0, 0)

        viewLayout.addWidget(self.link_list)

        self.link_list.itemClicked.connect(self.on_list_item_clicked)

    def add_link(self, icon: Union[str, QIcon, FluentIcon], text: str, url: str):
        item = QListWidgetItem(f"   {text}", self.link_list)
        item.setIcon(icon.icon())
        item.setData(Qt.ItemDataRole.UserRole, url)

        self.link_list.addItem(item)

    def on_list_item_clicked(self, item: QListWidgetItem):
        url = item.data(Qt.ItemDataRole.UserRole)

        signal_bus.parse.parse_url.emit(url)

        self.parent_widget.closed.emit()

class FavoriteFlyoutMenu(FlyoutViewBase):
    closed = Signal()

    def __init__(self, parent = None):
        super().__init__(parent)

        self.init_UI()

        self.init_favorite_list()
        self.init_subscription_list()

    def init_UI(self):
        self.category_widget = CategoryWidget(self)

        separator = Separator(self)

        self.favorite_widget = LinkWidget(self)
        self.subscribtion_widget = LinkWidget(self)

        self.stack_widget = QStackedWidget(self)
        self.stack_widget.addWidget(self.favorite_widget)
        self.stack_widget.addWidget(self.subscribtion_widget)

        self.viewLayout = QHBoxLayout(self)
        self.viewLayout.setContentsMargins(10, 10, 10, 10)
        self.viewLayout.setSpacing(0)
        self.viewLayout.addWidget(self.category_widget)
        self.viewLayout.addWidget(separator)
        self.viewLayout.addWidget(self.stack_widget)

    def init_favorite_list(self):
        for entry in config.user_favorite_list:
            mid = entry.get("mid", "")
            title = entry.get("title", "")
            fid = entry.get("id", "")

            url = "https://space.bilibili.com/{mid}/favlist?fid={fid}".format(mid = mid, fid = fid)

            self.favorite_widget.add_link(ExtendedFluentIcon.FAVORITE, title, url)

    def init_subscription_list(self):
        pass
        # for entry in config.user_subscription_list:
        #     title = entry.get("title", "")
        #     url = "https://space.bilibili.com/{mid}/channel/seriesdetail?sid={sid}".format(mid = entry.get("mid", ""), sid = entry.get("id", ""))

        #     self.subscribtion_widget.add_link(ExtendedFluentIcon.ALBUM, title, url)

    def on_category_changed(self, index: int):
        self.stack_widget.setCurrentIndex(index)
