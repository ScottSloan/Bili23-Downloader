from qfluentwidgets import ListView

from gui.component.entry_list.model import EntryListModel
from gui.component.entry_list.item_delegate import EntryListItemDelegate

class EntryListView(ListView):
    def __init__(self, parent = None):
        super().__init__(parent)

        self._model = EntryListModel([], self)
        self._delegate = EntryListItemDelegate(self)

        self.setModel(self._model)
        self.setItemDelegate(self._delegate)
        self.setSelectionMode(ListView.SelectionMode.SingleSelection)
        self.setSelectRightClickedRow(True)

        self.setUniformItemSizes(True)

    def add_entry_list(self, entry_list: list):
        for entry in entry_list:
            self._model.appendRow(entry)
