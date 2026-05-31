from PySide6.QtWidgets import QVBoxLayout, QWidget, QHBoxLayout
from PySide6.QtGui import QColor, QPainter, QPen
from PySide6.QtCore import Signal, QSize

from qfluentwidgets import (
    FlyoutViewBase, FluentIcon, isDarkTheme, ComboBox, PopUpAniStackedWidget, NavigationWidget
)

from gui.component.entry_list import EntryListView
from .button import TransparentToolButton
from .navigation import NavigationPanel
from .pager import Pager

from util.parse.parser.favorite import FavoriteParser
from util.common.icon import ExtendedFluentIcon
from util.common.signal_bus import signal_bus
from util.common.config import config

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
        filter_box.setContentsMargins(5, 5, 5, 5)
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
        self.category_widget = NavigationPanel(self)

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

        category_layout = QVBoxLayout()
        category_layout.setContentsMargins(0, 0, 5, 0)
        category_layout.addWidget(self.category_widget)
        category_layout.addLayout(btn_layout)

        self.separator = Separator(self)

        self.favorite_widget = EntryWidget(self)
        self.favorite_widget.setObjectName("favorite")

        self.subscribtion_widget = EntryWidget(self)
        self.subscribtion_widget.setObjectName("subscription")

        self.follow_widget = FollowWidget(self)
        self.follow_widget.setObjectName("follow")

        self.stack_widget = PopUpAniStackedWidget(self)
        self.stack_widget.setContentsMargins(0, 5, 0, 5)
        self.stack_widget.addWidget(self.favorite_widget)
        self.stack_widget.addWidget(self.subscribtion_widget)
        self.stack_widget.addWidget(self.follow_widget)

        self.viewLayout = QHBoxLayout(self)
        self.viewLayout.setContentsMargins(10, 10, 10, 10)
        self.viewLayout.setSpacing(0)
        self.viewLayout.addLayout(category_layout)
        self.viewLayout.addWidget(self.separator)
        self.viewLayout.addWidget(self.stack_widget, stretch = 1)

        self.init_category_list()

    def init_category_list(self):
        self.add_category(
            routeKey = "favorite",
            icon = ExtendedFluentIcon.FAVORITE,
            text = self.tr("Favorites"),
            widget = self.favorite_widget
        )
        self.add_category(
            routeKey = "subscription",
            icon = ExtendedFluentIcon.ALBUM,
            text = self.tr("Subscriptions"),
            widget = self.subscribtion_widget
        )
        self.add_category(
            routeKey = "follow",
            icon = FluentIcon.HEART,
            text = self.tr("Anime & Series"),
            widget = self.follow_widget
        )

        self.add_category(
            routeKey = "watch_later",
            icon = ExtendedFluentIcon.CLOCK,
            text = self.tr("Watch later"),
            onClick = lambda: self.on_parse_url("bili23://watch_later"),
            selectable = False,
        )
        self.add_category(
            routeKey = "history",
            icon = FluentIcon.HISTORY,
            text = self.tr("History"),
            onClick = lambda: self.on_parse_url("bili23://history"),
            selectable = False,
        )

        self.category_widget.setCurrentItem("favorite")

        self.open_in_browser_btn.clicked.connect(self.on_open_in_browser)
        self.refresh_btn.clicked.connect(self.init_flyout)

    def init_flyout(self):
        # 初始化数据
        self.favorite_parser.parse_favorite_list()
        self.subscribtion_parser.parse_subscription_list()
        self.follow_widget.update_list()

    def adjust_list_widget_width(self, parent_size: QSize):
        if parent_size.width() >= 1250:
            width = 1130        # 显示三列
        else:
            width = 830        # 显示两列

        if parent_size.height() >= 700:
            height = 655
        else:
            height = 475

        self.separator.setFixedHeight(height - 25)

        self.setFixedSize(width, height)

    def on_category_changed(self, index: int):
        self.stack_widget.setCurrentIndex(index)

    def on_parse_url(self, url: str):
        self.closed.emit()

        signal_bus.parse.parse_url.emit(url)

    def add_category(self, routeKey: str, icon, text, widget: QWidget = None, onClick = None, selectable = True):
        if widget:
            self.stack_widget.addWidget(widget)
            routeKey = widget.objectName()

        if onClick is None:
            onClick =  lambda: self.stack_widget.setCurrentWidget(widget)

        self.category_widget.addItem(
            routeKey,
            icon,
            text,
            onClick,
            selectable = selectable,
        )

    def on_open_in_browser(self):
        match self.stack_widget.currentIndex():
            case 0 | 1:
                url = "https://space.bilibili.com/{uid}/favlist".format(uid = config.user_uid)

            case 2:
                url = "https://space.bilibili.com/{uid}/bangumi".format(uid = config.user_uid)

        webbrowser.open(url)