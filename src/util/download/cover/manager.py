from PySide6.QtCore import Qt, QAbstractListModel, QSize
from PySide6.QtGui import QPixmap

from util.download.cover.query_worker import QueryWorker
from util.download.cover.db import CoverDatabase
from util.download.cover.cache import CoverCache
from util.thread import GlobalThreadPoolTask

from functools import lru_cache
from hashlib import md5

class CoverManager:
    def __init__(self):
        self.db_manager = CoverDatabase()

    @lru_cache(maxsize = None)
    def arrange_cover_id(self, cover_url: str):
        # 使用 cover_url 的 md5 作为 cover_id
        hash = md5(cover_url.encode("utf-8")).hexdigest()

        return hash

    def create(self, cover_id: str, cover_data: bytes):
        self.db_manager.add_cover(cover_id, cover_data)

    def query(self, cover_id: str):
        return self.db_manager.query_cover(cover_id)
    
    def request(self, model: QAbstractListModel, cover_id: str, cover_url: str, cover_size: QSize):
        worker = QueryWorker(model, cover_id, cover_url, cover_size)

        GlobalThreadPoolTask.run(worker)

    def placeholder(self):
        placeholder_pixmap = QPixmap(":/bili23/image/placeholder.png")
        placeholder_pixmap.scaled(144, 81, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

        return placeholder_pixmap
    
    def updateCache(self, cover_id: str, cover_data: bytes):
        if cover_id not in CoverCache.cache:
            CoverCache.cache[cover_id] = cover_data

    def getCache(self, cover_id: str):
        return CoverCache.cache.get(cover_id, None)

cover_manager = CoverManager()
    