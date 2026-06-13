from PySide6.QtCore import QModelIndex, Qt, QSortFilterProxyModel


class LogListProxyModel(QSortFilterProxyModel):
    def __init__(self, parent = None):
        super().__init__(parent)

        self._level_filter = "ALL"
        self._filter_text = ""

        self.setDynamicSortFilter(True)

    def _source(self):
        return self.sourceModel()

    def _matches_filter(self, record: dict):
        if self._level_filter != "ALL" and record.get("level", "").upper() != self._level_filter:
            return False

        if self._filter_text:
            keyword = self._filter_text.casefold()
            searchable_text = " ".join([
                record.get("timestamp", ""),
                record.get("name", ""),
                record.get("level", ""),
                record.get("message", ""),
            ]).casefold()

            if keyword not in searchable_text:
                return False

        return True

    def filterAcceptsRow(self, source_row: int, source_parent: QModelIndex):
        source = self._source()

        if not source:
            return False

        record = source.index(source_row, 0, source_parent).data(Qt.ItemDataRole.UserRole)

        if not record:
            return False

        return self._matches_filter(record)

    def setLevelFilter(self, level: str):
        self._level_filter = (level or "ALL").upper()
        self.invalidateFilter()

    def setFilterText(self, text: str):
        self._filter_text = text or ""
        self.invalidateFilter()

    def appendRow(self, entry):
        source = self._source()

        if source:
            source.appendRow(entry)

    def appendRows(self, entry_list: list):
        source = self._source()

        if source:
            source.appendRows(entry_list)

    def clearData(self):
        source = self._source()

        if source:
            source.clearData()