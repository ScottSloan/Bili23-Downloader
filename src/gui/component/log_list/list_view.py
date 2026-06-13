from qfluentwidgets import ListView

from .item_delegate import LogListItemDelegate
from .model import LogListModel
from .proxy_model import LogListProxyModel

class LogListView(ListView):
    def __init__(self, parent = None):
        super().__init__(parent)

        self._emptyTextTip = self.tr("No logs")

        self._source_model = LogListModel([], self)
        self._model = LogListProxyModel(self)
        self._model.setSourceModel(self._source_model)
        self._delegate = LogListItemDelegate(self)

        self.setModel(self._model)
        self.setItemDelegate(self._delegate)
        self.setSelectionMode(ListView.SelectionMode.SingleSelection)
        self.setSelectRightClickedRow(True)

        self.setUniformItemSizes(True)

    def updateGeometries(self):
        super().updateGeometries()

        self.verticalScrollBar().setSingleStep(30)

    def setLevelFilter(self, level: str):
        self._model.setLevelFilter(level)

    def setFilterText(self, text: str):
        self._model.setFilterText(text)
