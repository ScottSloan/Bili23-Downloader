from PySide6.QtCore import Qt, QAbstractListModel, QSize, QThreadPool
from PySide6.QtGui import QPixmap

from .query_worker import CoverQueryWorker
from .db import CoverDatabase
from .cache import CoverCache

from functools import lru_cache
from hashlib import md5

# 内存中缓存的封面张数上限。封面按设备像素存放，DPR 1.5 下单张约 100KB，
# 而列表滚动会让每一个被绘制过的条目都进缓存且原先没有任何淘汰机制
_COVER_CACHE_SIZE = 256

@lru_cache(maxsize = 8192)
def _calc_cover_id(cover_url: str):
    # 使用 cover_url 的 md5 作为 cover_id
    return md5(cover_url.encode("utf-8")).hexdigest()

# 占位图缓存，惰性填充。cover_manager 是导入期实例化的，在模块级构造 QPixmap 会要求
# QGuiApplication 已存在，从而把 Qt 图形栈拖进启动路径（见 smoke_startup.py）。
#
# 这里不用 lru_cache：资源尚未注册时拿到的是空图，被缓存下来就会永远返回空白占位图，
# 而缓存是否被污染完全取决于首次调用的时机。只在成功缩放后写入
_PLACEHOLDER_CACHE: dict = {}

def _calc_placeholder(width: int, height: int):
    # 占位图同样按物理尺寸取，理由与封面一致：按逻辑尺寸生成的话高 DPI 屏上还会被放大一次。
    # 顺带把结果缓存住 —— 原先每次 paint 都要重新从资源里加载 PNG 再缩放一遍
    key = (width, height)

    if key in _PLACEHOLDER_CACHE:
        return _PLACEHOLDER_CACHE[key]

    pixmap = QPixmap(":/bili23/image/placeholder.png")

    if pixmap.isNull():
        return pixmap

    scaled = pixmap.scaled(QSize(width, height), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

    _PLACEHOLDER_CACHE[key] = scaled

    return scaled

class CoverManager:
    def __init__(self):
        self.db_manager = CoverDatabase()

        # 为封面加载专门创建一个独立的线程池
        self.thread_pool = QThreadPool()

        # 作为典型的网络/数据库 I/O 密集型任务，可适当增加最大线程数并发处理
        self.thread_pool.setMaxThreadCount(16)

    def arrange_cover_id(self, cover_url: str):
        # 缓存放在模块级函数上：装饰实例方法会把 self 一并作为缓存键持有，且原先没有上限
        return _calc_cover_id(cover_url)

    def arrange_cover_key(self, cover_id: str, cover_size: QSize):
        """封面缓存与数据库中的键：cover_id 加上像素尺寸

        封面缓存是所有列表共用的，而各列表要的尺寸并不相同（解析列表 128x72、下载列表
        144x80）。同一个 cover_id 只留一份的话，谁先请求谁就决定了缓存里存哪一档尺寸，
        后到的消费方拿到不匹配的图还得再缩放一次 —— 照样是模糊。并入尺寸后各取所需。
        """
        return f"{cover_id}@{cover_size.width()}x{cover_size.height()}"
    
    def create(self, cover_key: str, cover_data: bytes):
        self.db_manager.add_cover(cover_key, cover_data)

    def query(self, cover_key: str):
        return self.db_manager.query_cover(cover_key)

    def request(self, model: QAbstractListModel, cover_key: str, cover_url: str, cover_size: QSize, query_param: dict = None):
        worker = CoverQueryWorker(model, cover_key, cover_url, cover_size, query_param)

        self.thread_pool.start(worker)

    def placeholder(self, cover_size: QSize):
        return _calc_placeholder(cover_size.width(), cover_size.height())

    # 注意与 create() 的区别：这里收的是已经解码好的位图，create() 收的是待入库的 webp 字节
    def updateCache(self, cover_key: str, pixmap: QPixmap):
        cache = CoverCache.cache
    
        if cover_key in cache:
            return

        cache[cover_key] = pixmap

        if len(cache) > _COVER_CACHE_SIZE:
            # OrderedDict + getCache 里的 move_to_end 构成 LRU，淘汰最久未访问的那张
            cache.popitem(last = False)

    def getCache(self, cover_key: str):
        pixmap = CoverCache.cache.get(cover_key)

        if pixmap is not None:
            CoverCache.cache.move_to_end(cover_key)

        return pixmap

cover_manager = CoverManager()
    