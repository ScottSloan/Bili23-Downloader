from PySide6.QtCore import QModelIndex, Qt, QSize

from gui.component.view_model import CoverQueryModelBase

class EntryListModel(CoverQueryModelBase):
    def __init__(self, entry_list: list, parent = None):
        super().__init__(parent)

        self._cover_size = QSize(120, 67)
        self._entry_list = entry_list

        self.setQueryCoverParam(
            {
                # 一次请求同时拿到收藏夹信息（data.info.cover）和第一个视频
                # （data.medias[0].cover）。api_url 指向 resource/list，
                # 额外参数（pn=1、ps=1 等）由 CoverQueryWorker.query_url() 合并
                "api_url": "https://api.bilibili.com/x/v3/fav/resource/list",
                # 显式开关：只有收藏夹列表才走"一次 resource/list 同时拿
                # info + medias"的路径，并按 info.cover → medias[0].cover 顺序取。
                # __query__ 是通用机制，未来复用到其他列表时默认不启用该路径
                "fallback_first_media_cover": True
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

