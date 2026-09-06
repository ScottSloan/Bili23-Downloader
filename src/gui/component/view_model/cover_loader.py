"""
封面的异步加载与缓存（界面侧）

原先这部分和 `arrange_cover_id` 一起放在 `util/download/cover/manager.py` 里，
但那个模块被 `task/manager.py` 与 `parser/favorite.py` 引用，而它们在 WebUI 侧也要用（D16）——
QThreadPool、QPixmap、QAbstractListModel 一个都不能留在那边。

于是按「谁在用」拆开：算标识、读写封面库留在 core，取图与缓存搬到这里。
WebUI 那边把封面地址直接交给浏览器加载，本文件对它没有意义。
"""

from PySide6.QtCore import Qt, QAbstractListModel, QSize, QThreadPool
from PySide6.QtGui import QPixmap

from .cover_cache import CoverCache
from .cover_worker import CoverQueryWorker

class CoverLoader:
    def __init__(self):
        # 封面加载专用的独立线程池，不与解析、下载争抢
        self.thread_pool = QThreadPool()

        # 典型的网络 / 数据库 I/O 密集型任务，线程数可以给得比 CPU 核数多
        self.thread_pool.setMaxThreadCount(16)

    def request(self, model: QAbstractListModel, query_id: str, cover_id: str, cover_url: str,
                cover_size: QSize, query_param: dict = None):
        worker = CoverQueryWorker(model, query_id, cover_id, cover_url, cover_size, query_param)

        self.thread_pool.start(worker)

    def placeholder(self, cover_size: QSize):
        placeholder_pixmap = QPixmap(":/bili23/image/placeholder.png")

        return placeholder_pixmap.scaled(
            cover_size, Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

    def update_cache(self, cover_id: str, pixmap: QPixmap):
        if cover_id not in CoverCache.cache:
            CoverCache.cache[cover_id] = pixmap

    def get_cache(self, cover_id: str):
        return CoverCache.cache.get(cover_id, None)

cover_loader = CoverLoader()
