from PySide6.QtCore import Qt, QRect, QPoint
from PySide6.QtWidgets import QWidget

from qfluentwidgets import (
    NavigationWidget, NavigationTreeWidget, NavigationDisplayMode
)
from qfluentwidgets.components.navigation.navigation_panel import (
    NavigationItem, NavigationToolTipFilter, NavigationItemLayout
)
from qfluentwidgets.components.navigation.navigation_widget import NavigationIndicator

from typing import Dict

class NavigationPanel(QWidget):
    def __init__(self, parent = None):
        super().__init__(parent = parent)

        self.indicator = NavigationIndicator(self)

        self._isIndicatorAnimationEnabled = True

        self.items = {}   # type: Dict[str, NavigationItem]
        self._currentRouteKey = None

        self.vBoxLayout = NavigationItemLayout(self)
        self.topLayout = NavigationItemLayout()

        self.displayMode = NavigationDisplayMode.EXPAND

        NavigationWidget.EXPAND_WIDTH = 180

        self.__initWidget()
        self.__initLayout()

    def __initWidget(self):
        self.setAttribute(Qt.WidgetAttribute.WA_StyledBackground)

        self.indicator.aniFinished.connect(self._onIndicatorAniFinished)

    def __initLayout(self):
        self.vBoxLayout.setContentsMargins(0, 5, 0, 5)
        self.topLayout.setContentsMargins(4, 0, 4, 0)
        self.vBoxLayout.setSpacing(4)
        self.topLayout.setSpacing(4)

        self.vBoxLayout.addLayout(self.topLayout, 0)
        self.vBoxLayout.addStretch(1)

    def _onIndicatorAniFinished(self):
        item = self.currentItem()

        item.setSelected(True)
        
        indicatorItem = self._findIndicatorItem(item)

        if indicatorItem:
            indicatorItem.setAboutSelected(False)

        self.indicator.hide()

    def setCurrentItem(self, routeKey: str):
        if routeKey not in self.items or routeKey == self._currentRouteKey:
            return

        prevItem = self.currentItem()
        self._currentRouteKey = routeKey

        # find the items to display indicator animation
        newItem = self.currentItem()
        newIndicatorItem = self._findIndicatorItem(newItem)
        prevIndicatorItem = self._findIndicatorItem(prevItem)

        # early return if indicator is not enabled or previous selected item is None
        if not (self.isIndicatorAnimationEnabled() and prevItem and prevIndicatorItem and newIndicatorItem):
            for k, item in self.items.items():
                item.widget.setSelected(k == routeKey)

            return

        # calculate the start and final geometry for animation
        preIndicatorRect = self._getIndicatorRect(prevIndicatorItem)
        newIndicatorRect = self._getIndicatorRect(newIndicatorItem)

        # start animation
        prevItem.setSelected(False)
        prevIndicatorItem.setSelected(False)
        newIndicatorItem.setAboutSelected(True)
        self.indicator.setIndicatorColor(newItem.lightIndicatorColor, newItem.darkIndicatorColor)
        self.indicator.startAnimation(preIndicatorRect, newIndicatorRect)

    def currentItem(self):
        return self.widget(self._currentRouteKey) if self._currentRouteKey else None
    
    def _getIndicatorRect(self, item: NavigationWidget):
        if not item:
            return QRect()

        pos = item.mapTo(self, QPoint(0, 0))
        rect = item.indicatorRect()
        return rect.translated(pos)
    
    def widget(self, routeKey: str):
        return self.items[routeKey].widget
    
    def _findIndicatorItem(self, item: NavigationWidget):
        parent = item
        while parent:
            if isinstance(parent, NavigationWidget) and parent.isVisible():
                break

            parent = parent.parent()

        return parent
    
    def addItem(self, routeKey: str, icon, text: str, onClick = None, selectable = True,
                tooltip: str = None):
        
        return self.insertItem(-1, routeKey, icon, text, onClick, selectable, tooltip)
    
    def insertItem(self, index: int, routeKey: str, icon, text: str, onClick = None,
                   selectable = True, tooltip: str = None):
        
        w = NavigationTreeWidget(icon, text, selectable, self)
        w.setFixedWidth(100)
        self.insertWidget(index, routeKey, w, onClick, tooltip)
        return w
    
    def insertWidget(self, index: int, routeKey: str, widget: NavigationWidget, onClick = None,
                     tooltip: str = None):
        
        self._registerWidget(routeKey, widget, onClick, tooltip)
        self._insertWidgetToLayout(index, widget)

    def _registerWidget(self, routeKey: str, widget: NavigationWidget, onClick, tooltip: str):
        widget.clicked.connect(self._onWidgetClicked)

        if onClick is not None:
            widget.clicked.connect(onClick)

        widget.setProperty('routeKey', routeKey)
        widget.setProperty('parentRouteKey', None)
        self.items[routeKey] = NavigationItem(routeKey, None, widget)

        widget.setCompacted(False)

        if tooltip:
            widget.setToolTip(tooltip)
            widget.installEventFilter(NavigationToolTipFilter(widget, 1000))

    def _insertWidgetToLayout(self, index: int, widget: NavigationWidget):
        widget.setParent(self)
        self.topLayout.insertWidget(index, widget, 0, Qt.AlignmentFlag.AlignTop)

        widget.show()

    def _onWidgetClicked(self):
        widget = self.sender()  # type: NavigationWidget

        if not widget.isSelectable:
            return

        self.setCurrentItem(widget.property('routeKey'))

    def isIndicatorAnimationEnabled(self):
        return self._isIndicatorAnimationEnabled
