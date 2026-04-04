from PySide6.QtWidgets import QVBoxLayout, QWidget, QHBoxLayout, QStackedWidget, QListWidgetItem
from PySide6.QtGui import QColor, QIcon, QPainter, QPen
from PySide6.QtCore import Signal, Qt, QSize

from qfluentwidgets import (
    FlyoutViewBase, FluentIcon, isDarkTheme, ListWidget
)
from qfluentwidgets.components.navigation import NavigationWidget

from gui.component.entry_list.list_view import EntryListView

from util.common import ExtendedFluentIcon, config, signal_bus

from typing import Union

class Separator(NavigationWidget):
    def __init__(self, parent = None):
        super().__init__(False, parent=parent)

        self.setFixedSize(5, 350)

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
                "text": self.tr("Favorites"),
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
                "text": self.tr("Watch later"),
                "data": {
                    "isSelectable": False,
                    "url": "bili23://watch_later"
                }
            },
            {
                "icon": FluentIcon.HISTORY,
                "text": self.tr("History"),
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

class EntryWidget(QWidget):
    def __init__(self, parent: 'FavoriteFlyoutMenu'):
        super().__init__(parent)

        self.parent_widget = parent

        self.init_UI()

    def init_UI(self):
        self.entry_list = EntryListView(self)
        self.entry_list.setFixedWidth(375)

        viewLayout = QVBoxLayout(self)
        viewLayout.setContentsMargins(5, 0, 0, 0)

        viewLayout.addWidget(self.entry_list)

        self.entry_list._model.itemClicked.connect(self.on_list_item_clicked)

    def on_list_item_clicked(self, index, entry: dict):
        url = entry.get("url", "")

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

        self.favorite_widget = EntryWidget(self)
        self.subscribtion_widget = EntryWidget(self)

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
        entry_list = []

        for entry in config.user_favorite_list:
            title = entry.get("title", "")
            mid = entry.get("mid", "")
            fid = entry.get("id", "")
            count = entry.get("media_count", 0)

            entry_list.append({
                "title": title,
                "url": "https://space.bilibili.com/{mid}/favlist?fid={fid}".format(mid = mid, fid = fid),
                "count": count
            })

        self.favorite_widget.entry_list.add_entry_list(entry_list)

    def init_subscription_list(self):
        entry_list = []

        for entry in config.user_subscription_list:
            title = entry.get("title", "")
            mid = entry.get("mid", "")
            id = entry.get("id", "")
            count = entry.get("media_count", 0)

            entry_list.append({
                "title": title,
                "url": "https://space.bilibili.com/{mid}/lists/{id}?type=season".format(mid = mid, id = id),
                "count": count
            })

        self.subscribtion_widget.entry_list.add_entry_list(entry_list)

    def on_category_changed(self, index: int):
        self.stack_widget.setCurrentIndex(index)
