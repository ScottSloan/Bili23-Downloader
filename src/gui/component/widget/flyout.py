from PySide6.QtWidgets import QVBoxLayout, QWidget, QHBoxLayout, QListWidgetItem
from PySide6.QtGui import QColor, QIcon, QPainter, QPen
from PySide6.QtCore import Signal, Qt, QSize

from qfluentwidgets import (
    FlyoutViewBase, FluentIcon, isDarkTheme, ListWidget, ComboBox, PopUpAniStackedWidget
)
from qfluentwidgets.components.navigation import NavigationWidget

from gui.component.entry_list import EntryListView

from .button import TransparentToolButton
from .pager import Pager

from util.common import ExtendedFluentIcon, signal_bus, config
from util.parse.parser import FavoriteParser

from typing import Union
import webbrowser

class Separator(NavigationWidget):
    def __init__(self, parent = None):
        super().__init__(False, parent = parent)

        self.setFixedWidth(5)

        self.update()

    def paintEvent(self, e):
        painter = QPainter(self)

        c = 255 if isDarkTheme() else 0

        pen = QPen(QColor(c, c, c, 25))
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

        self.refresh_btn = TransparentToolButton(ExtendedFluentIcon.RETRY, parent = self)
        self.refresh_btn.setToolTip(self.tr("Refresh"))
        self.refresh_btn.setFixedHeight(32)

        self.open_in_browser_btn = TransparentToolButton(FluentIcon.GLOBE, parent = self)
        self.open_in_browser_btn.setToolTip(self.tr("Open in Browser"))
        self.open_in_browser_btn.setFixedHeight(32)

        btn_layout = QHBoxLayout()
        btn_layout.setContentsMargins(0, 0, 0, 0)
        btn_layout.setSpacing(5)
        btn_layout.addWidget(self.refresh_btn)
        btn_layout.addWidget(self.open_in_browser_btn)
        btn_layout.addStretch()

        viewLayout = QVBoxLayout(self)
        viewLayout.setContentsMargins(0, 0, 5, 0)

        viewLayout.addWidget(self.category_list)
        viewLayout.addLayout(btn_layout)

        self.open_in_browser_btn.clicked.connect(self.on_open_in_browser)

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

        parent_widget: 'FavoriteFlyoutWidget' = self.parent()

        if data["isSelectable"]:
            parent_widget.on_category_changed(self.category_list.row(item))
        
        else:
            parent_widget.closed.emit()
            
            signal_bus.parse.parse_url.emit(data["url"])

    def on_open_in_browser(self):
        match self.category_list.currentIndex().row():
            case 0 | 1:
                url = "https://space.bilibili.com/{uid}/favlist".format(uid = config.user_uid)

            case 2:
                url = "https://space.bilibili.com/{uid}/bangumi".format(uid = config.user_uid)

        webbrowser.open(url)

class EntryWidget(QWidget):
    def __init__(self, parent: 'FavoriteFlyoutWidget'):
        super().__init__(parent)

        self.parent_widget = parent
        self.manual_request_cover_needed = False

        self.init_UI()

    def init_UI(self):
        self.entry_list = EntryListView(is_poster = False, parent = self)
        self.entry_list.set_cover_size(QSize(128, 72))
        self.entry_list.setWrappingView()

        viewLayout = QVBoxLayout(self)
        viewLayout.setContentsMargins(5, 0, 0, 0)

        viewLayout.addWidget(self.entry_list)

        self.entry_list._model.itemClicked.connect(self.on_list_item_clicked)
        self.entry_list.parse.connect(self.on_list_item_clicked)

    def on_list_item_clicked(self, index, entry: dict):
        url = entry.get("url", "")

        signal_bus.parse.parse_url.emit(url)

        self.parent_widget.closed.emit()

    def update_list(self, entry_list: list):
        self.entry_list._model.clearData()

        self.entry_list.add_entry_list(entry_list)

        if self.manual_request_cover_needed:
            pass

    def set_manual_request_cover_needed(self, needed: bool):
        self.manual_request_cover_needed = needed

class FollowWidget(QWidget):
    query_success = Signal(list, dict)

    def __init__(self, parent: 'FavoriteFlyoutWidget'):
        super().__init__(parent)

        self.parent_widget = parent
        self.pn = 1

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
        self.entry_list.set_cover_size(QSize(123, 164))
        self.entry_list.setWrappingView()

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

        self.connect_signals()

    def connect_signals(self):
        self.entry_list._model.itemClicked.connect(self.on_list_item_clicked)
        self.entry_list.parse.connect(self.on_list_item_clicked)
        self.type_choice.currentIndexChanged.connect(self.update_list)
        self.status_choice.currentIndexChanged.connect(self.update_list)

        self.pager.pageChanged.connect(self.on_page_changed)

    def init_utils(self):
        self.parser = FavoriteParser()
        self.parser.success_callback = self.query_success.emit
        
        self.query_success.connect(self.on_query_success)

    def on_query_success(self, entry_list: list, extra_data: dict):
        self.entry_list.add_entry_list(entry_list)

        pagination_data = extra_data.get("pagination_data", {})

        self.pager.update_data(pagination_data)

    def on_list_item_clicked(self, index, entry: dict):
        url = entry.get("url", "")

        signal_bus.parse.parse_url.emit(url)

        self.parent_widget.closed.emit()

    def on_page_changed(self, page: int):
        self.pn = page

        self.update_list()

    def update_list(self):
        self.entry_list._model.clearData()

        type = self.type_choice.currentIndex() + 1
        follow_status = self.status_choice.currentIndex()

        self.parser.parse_follow_list(self.pn, type, follow_status)

class FavoriteFlyoutWidget(FlyoutViewBase):
    closed = Signal()

    def __init__(self, parent = None):
        super().__init__(parent)

        self.init_UI()

        self.favorite_parser = FavoriteParser()
        self.favorite_parser.success_callback = self.favorite_widget.update_list

        self.subscribtion_parser = FavoriteParser()
        self.subscribtion_parser.success_callback = self.subscribtion_widget.update_list

    def init_UI(self):
        self.category_widget = CategoryWidget(self)
        self.category_widget.setFixedWidth(180)

        self.separator = Separator(self)

        self.favorite_widget = EntryWidget(self)
        self.subscribtion_widget = EntryWidget(self)
        self.follow_widget = FollowWidget(self)

        self.stack_widget = PopUpAniStackedWidget(self)
        self.stack_widget.addWidget(self.favorite_widget)
        self.stack_widget.addWidget(self.subscribtion_widget)
        self.stack_widget.addWidget(self.follow_widget)

        self.viewLayout = QHBoxLayout(self)
        self.viewLayout.setContentsMargins(10, 10, 10, 10)
        self.viewLayout.setSpacing(0)
        self.viewLayout.addWidget(self.category_widget)
        self.viewLayout.addWidget(self.separator)
        self.viewLayout.addWidget(self.stack_widget)
        
        self.category_widget.refresh_btn.clicked.connect(self.init_flyout)

    def init_flyout(self):
        # 初始化数据
        self.favorite_parser.parse_favorite_list()
        self.subscribtion_parser.parse_subscription_list()
        self.follow_widget.update_list()

    def adjust_list_widget_width(self, parent_size: QSize):
        if parent_size.width() >= 1250:
            width = 1110        # 显示三列
        else:
            width = 810        # 显示两列

        if parent_size.height() >= 700:
            height = 655
        else:
            height = 475

        self.separator.setFixedHeight(height - 25)

        self.setFixedSize(width, height)

    def on_category_changed(self, index: int):
        self.stack_widget.setCurrentIndex(index)
