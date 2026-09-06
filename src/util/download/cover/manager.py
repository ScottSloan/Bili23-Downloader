"""
封面的标识与持久化

**只留不依赖 Qt 的部分。** 封面的异步加载与 QPixmap 缓存属于界面渲染，
已移到 `gui/component/view_model/cover_loader.py` ——
这个模块被 `task/manager.py` 与 `parser/favorite.py` 引用，而它们在 WebUI 侧也要用（D16）。

WebUI 那边不需要 QPixmap：封面地址直接交给浏览器加载即可，
它要的只是 `arrange_cover_id` 算出来的那个标识。
"""

from functools import lru_cache
from hashlib import md5

from .db import CoverDatabase

@lru_cache(maxsize = 8192)
def _calc_cover_id(cover_url: str):
    # 使用 cover_url 的 md5 作为 cover_id
    return md5(cover_url.encode("utf-8")).hexdigest()

class CoverManager:
    def __init__(self):
        self.db_manager = CoverDatabase()

    def arrange_cover_id(self, cover_url: str):
        # 缓存放在模块级函数上：装饰实例方法会把 self 一并作为缓存键持有，且原先没有上限
        return _calc_cover_id(cover_url)

    def create(self, cover_id: str, cover_data: bytes):
        self.db_manager.add_cover(cover_id, cover_data)

    def query(self, cover_id: str):
        return self.db_manager.query_cover(cover_id)

cover_manager = CoverManager()
