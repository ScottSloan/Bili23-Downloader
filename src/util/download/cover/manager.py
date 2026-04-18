from PySide6.QtCore import Qt, QAbstractListModel, QSize, QThreadPool
from PySide6.QtGui import QPixmap

from .query_worker import CoverQueryWorker
from .db import CoverDatabase
from .cache import CoverCache

from functools import lru_cache
from hashlib import md5

class CoverManager:
    def __init__(self):
        self.db_manager = CoverDatabase()

        # 为封面加载专门创建一个独立的线程池
        self.thread_pool = QThreadPool()
        
        # 作为典型的网络/数据库 I/O 密集型任务，可适当增加最大线程数并发处理
        self.thread_pool.setMaxThreadCount(16)

    @lru_cache(maxsize = None)
    def arrange_cover_id(self, cover_url: str):
        # 使用 cover_url 的 md5 作为 cover_id
        hash = md5(cover_url.encode("utf-8")).hexdigest()

        return hash

    def create(self, cover_id: str, cover_data: bytes):
        self.db_manager.add_cover(cover_id, cover_data)

    def query(self, cover_id: str):
        return self.db_manager.query_cover(cover_id)
    
    def request(self, model: QAbstractListModel, query_id: str, cover_id: str, cover_url: str, cover_size: QSize, query_param: dict = None):
        worker = CoverQueryWorker(model, query_id, cover_id, cover_url, cover_size, query_param)

        self.thread_pool.start(worker)

    def placeholder(self, cover_size: QSize):
        placeholder_pixmap = QPixmap(":/bili23/image/placeholder.png")
        placeholder_pixmap = placeholder_pixmap.scaled(cover_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

        return placeholder_pixmap
    
    def updateCache(self, cover_id: str, cover_data: bytes):
        if cover_id not in CoverCache.cache:
            CoverCache.cache[cover_id] = cover_data

    def getCache(self, cover_id: str):
        return CoverCache.cache.get(cover_id, None)

cover_manager = CoverManager()
    