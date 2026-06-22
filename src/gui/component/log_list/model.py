from PySide6.QtCore import QAbstractListModel, Qt, QModelIndex

class LogListModel(QAbstractListModel):
    def __init__(self, log_list: list, parent = None):
        super().__init__(parent)

        self._log_list = log_list

    def rowCount(self, parent = QModelIndex()):
        return len(self._log_list)
    
    def data(self, index: QModelIndex, role = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return
        
        record: dict = self._log_list[index.row()]

        match role:
            case Qt.ItemDataRole.DisplayRole:
                return record.get("message", "")
            
            case Qt.ItemDataRole.UserRole:
                return record

    def appendRow(self, entry):
        row = self.rowCount()

        self.beginInsertRows(QModelIndex(), row, row)

        self._log_list.append(entry)

        self.endInsertRows()

    def appendRows(self, entry_list: list):
        row = self.rowCount()

        self.beginInsertRows(QModelIndex(), row, row + len(entry_list) - 1)

        self._log_list.extend(entry_list)

        self.endInsertRows()

    def clearData(self):
        self.beginResetModel()

        self._log_list.clear()

        self.endResetModel()