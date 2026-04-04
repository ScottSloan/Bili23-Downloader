from PySide6.QtWidgets import QVBoxLayout, QWidget, QHBoxLayout, QStackedWidget, QListWidgetItem
from PySide6.QtGui import QColor, QIcon, QPainter, QPen
from PySide6.QtCore import Signal, Qt, QSize

from qfluentwidgets import (
    FlyoutViewBase, FluentIcon, isDarkTheme, ListWidget, ComboBox
)
from qfluentwidgets.components.navigation import NavigationWidget

from gui.component.entry_list.list_view import EntryListView
from gui.component.widget.pager import Pager

from util.parse.parser.bangumi_follow import BangumiFollowParser
from util.common import ExtendedFluentIcon, config, signal_bus
from util.download.cover.manager import cover_manager

from typing import Union

class Separator(NavigationWidget):
    def __init__(self, parent = None):
        super().__init__(False, parent=parent)

        self.setFixedSize(5, 450)

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
                "text": self.tr("Subscriptions"),
                "data": {
                    "isSelectable": True,
                }
            },
            {
                "icon": FluentIcon.HEART,
                "text": self.tr("Anime & Series"),
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

        self.category_list.setCurrentRow(config.flyout_menu_category_index)

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
        self.entry_list = EntryListView(is_poster = False, parent = self)
        self.entry_list.setFixedWidth(425)
        self.entry_list.set_cover_size(QSize(128, 72))

        viewLayout = QVBoxLayout(self)
        viewLayout.setContentsMargins(5, 0, 0, 0)

        viewLayout.addWidget(self.entry_list)

        self.entry_list._model.itemClicked.connect(self.on_list_item_clicked)

    def on_list_item_clicked(self, index, entry: dict):
        url = entry.get("url", "")

        signal_bus.parse.parse_url.emit(url)

        self.parent_widget.closed.emit()

class FollowWidget(QWidget):
    query_success = Signal(list, dict)

    def __init__(self, parent: 'FavoriteFlyoutMenu'):
        super().__init__(parent)

        self.parent_widget = parent

        self.init_UI()

        self.init_utils()

    def init_UI(self):
        self.type_choice = ComboBox(self)
        self.type_choice.addItems(
            [
                self.tr("Anime"),
                self.tr("Series"),
            ]
        )

        self.status_choice = ComboBox(self)
        self.status_choice.addItems(
            [
                self.tr("All"),
                self.tr("Want to watch"),
                self.tr("Watching"),
                self.tr("Watched"),
            ]
        )

        self.entry_list = EntryListView(is_poster = True, parent = self)
        self.entry_list.setFixedWidth(425)
        self.entry_list.set_cover_size(QSize(123, 164))

        self.pager = Pager(self)

        filter_box = QHBoxLayout()
        filter_box.addWidget(self.type_choice)
        filter_box.addWidget(self.status_choice)

        viewLayout = QVBoxLayout(self)
        viewLayout.setContentsMargins(5, 0, 0, 0)
        viewLayout.setSpacing(10)

        viewLayout.addLayout(filter_box)
        viewLayout.addWidget(self.entry_list)
        viewLayout.addWidget(self.pager)

        self.connect_signal()

    def connect_signal(self):
        self.entry_list._model.itemClicked.connect(self.on_list_item_clicked)
        self.type_choice.currentIndexChanged.connect(self.update_list)
        self.status_choice.currentIndexChanged.connect(self.update_list)

        self.pager.pageChanged.connect(self.on_page_changed)

    def init_utils(self):
        self.parser = BangumiFollowParser()
        self.parser.success_callback = self.query_success.emit
        
        self.query_success.connect(self.on_query_success)

        self.update_list()

    def on_query_success(self, entry_list: list, extra_data: dict):
        self.entry_list.add_entry_list(entry_list)

        pagination_data = extra_data.get("pagination_data", {})

        self.pager.update_data(pagination_data)

    def on_list_item_clicked(self, index, entry: dict):
        url = entry.get("url", "")

        signal_bus.parse.parse_url.emit(url)

        self.parent_widget.closed.emit()

    def on_page_changed(self, page: int):
        config.flyout_menu_follow_list_page = page

        self.update_list()

    def update_list(self):
        self.entry_list._model.clearData()

        type = self.type_choice.currentIndex() + 1
        follow_status = self.status_choice.currentIndex()

        self.parser.parse(config.flyout_menu_follow_list_page, type, follow_status)

class FavoriteFlyoutMenu(FlyoutViewBase):
    closed = Signal()

    def __init__(self, parent = None):
        super().__init__(parent)

        self.init_UI()

        self.init_favorite_list()
        self.init_subscription_list()

        self.stack_widget.setCurrentIndex(config.flyout_menu_category_index)

    def init_UI(self):
        self.category_widget = CategoryWidget(self)

        separator = Separator(self)

        self.favorite_widget = EntryWidget(self)
        self.subscribtion_widget = EntryWidget(self)
        self.poster_widget = FollowWidget(self)

        self.stack_widget = QStackedWidget(self)
        self.stack_widget.addWidget(self.favorite_widget)
        self.stack_widget.addWidget(self.subscribtion_widget)
        self.stack_widget.addWidget(self.poster_widget)

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
            cover = entry.get("cover", "")

            entry_list.append({
                "title": title,
                "url": "https://space.bilibili.com/{mid}/lists/{id}?type=season".format(mid = mid, id = id),
                "count": count,
                "cover": cover,
                "cover_id": cover_manager.arrange_cover_id(cover)
            })

        self.subscribtion_widget.entry_list.add_entry_list(entry_list)

    def on_category_changed(self, index: int):
        self.stack_widget.setCurrentIndex(index)

        config.flyout_menu_category_index = index
