from qfluentwidgets import setCustomStyleSheet, setFont, PivotItem as _PivotItem, Pivot as _Pivot

class PivotItem(_PivotItem):
    def __init__(self, text: str, icon = None, parent = None):
        super().__init__(parent = parent)

        self.setText(text)

        if icon:
            self.setIcon(icon)

        self._set_custom_style()

    def _set_custom_style(self):
        light = """PivotItem:hover {color: rgba(0, 0, 0, 0.63);}"""
        dark = """PivotItem:hover {color: rgba(255, 255, 255, 0.63);}"""

        setCustomStyleSheet(self, light, dark)

    def setFontSize(self, size: int):
        setFont(self, size)

class Pivot(_Pivot):
    def __init__(self, parent = None):
        super().__init__(parent = parent)

    def addItem(self, routeKey: str, widget: PivotItem, onClick = None):
        if routeKey in self.items:
            return

        widget.setProperty('routeKey', routeKey)
        widget.itemClicked.connect(self._onItemClicked)

        if onClick:
            widget.itemClicked.connect(onClick)

        self.items[routeKey] = widget

        self.hBoxLayout.addWidget(widget)
