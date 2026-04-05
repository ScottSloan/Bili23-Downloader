from PySide6.QtCore import QAbstractListModel, Slot, QSize
from PySide6.QtGui import QImage, QPixmap

from util.download.cover.manager import cover_manager

from typing import Dict, Set

class CoverQueryModelBase(QAbstractListModel):
    """
    具有异步封面显示功能的模型基类
    """

    def __init__(self, parent = None):
        super().__init__(parent)

        self._cover_size = QSize(120, 67)
        self.cover_waiting_rows: Dict[str, Set[int]] = {}
    
    def queryRowCover(self, cover_id: str, cover_url: str, row: int) -> tuple[QPixmap, bool]:
        # 由委托发起查询封面请求

        if cover_id is None:
            return cover_manager.placeholder(), True

        # 命中缓存，直接返回
        if cahce := cover_manager.getCache(cover_id):
            return cahce, False

        # 记录等待该cover_id的所有row
        waiting_set = self.cover_waiting_rows.setdefault(cover_id, set())

        if row not in waiting_set:
            waiting_set.add(row)

            # 只在首次请求时启动worker
            if len(waiting_set) == 1:
                cover_manager.request(self, cover_id, cover_url, self._cover_size)

        return cover_manager.placeholder(), True

    @Slot(str, QImage)
    def updateRowCover(self, cover_id: str, image: QImage):
        # 缓存图片（回到 GUI 线程后再转成 QPixmap）
        pixmap = QPixmap.fromImage(image)
        cover_manager.updateCache(cover_id, pixmap)

        # 更新所有等待该cover_id的行
        if cover_id in self.cover_waiting_rows:

            rows = self.cover_waiting_rows[cover_id]

            for row in rows:
                index = self.index(row)
                self.dataChanged.emit(index, index)

            del self.cover_waiting_rows[cover_id]
