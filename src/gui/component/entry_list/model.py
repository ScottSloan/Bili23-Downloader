from PySide6.QtCore import QModelIndex, Qt, Signal, QSize

from gui.component.view_model import CoverQueryModelBase

class EntryListModel(CoverQueryModelBase):
    itemClicked = Signal(QModelIndex, object)

    def __init__(self, entry_list: list, parent = None):
        super().__init__(parent)

        self._cover_size = QSize(120, 67)
        self._entry_list = entry_list

        self.setQueryCoverParam(
            {
                "api_url": "https://api.bilibili.com/x/v3/fav/folder/info"
            }
        )

    def rowCount(self, parent = QModelIndex()):
        return len(self._entry_list)
    
    def data(self, index: QModelIndex, role = Qt.ItemDataRole.DisplayRole):
        if not index.isValid():
            return
        
        entry = self._entry_list[index.row()]
        
        match role:
            case Qt.ItemDataRole.DisplayRole:
                return entry["title"]
            
            case Qt.ItemDataRole.UserRole:
                return entry
            
            case Qt.ItemDataRole.ToolTipRole:
                return entry["title"]
            
    def appendRow(self, entry):
        row = self.rowCount()

        self.beginInsertRows(QModelIndex(), row, row)

        self._entry_list.append(entry)

        self.endInsertRows()

    def clearData(self):
        self.beginResetModel()

        self._entry_list.clear()

        self.endResetModel()

