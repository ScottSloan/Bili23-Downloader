from PySide6.QtCore import QModelIndex, Qt, QSize

from gui.component.view_model import CoverQueryModelBase

class EntryListModel(CoverQueryModelBase):
    def __init__(self, entry_list: list, parent = None):
        super().__init__(parent)

        self._cover_size = QSize(120, 67)
        self._entry_list = entry_list

        self.setQueryCoverParam(
            {
                "api_url": "https://api.bilibili.com/x/v3/fav/folder/info",
                # 没设封面的收藏夹改用其中第一个视频的封面，与 B 站页面一致。
                # 显式开关而不是在 worker 里按 URL 判断：__query__ 是通用机制，换个接口就会误触发
                "fallback_to_first_media": True
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

