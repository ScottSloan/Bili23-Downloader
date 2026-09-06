"""封面的 QPixmap 缓存。存的是 Qt 对象，只属于界面侧"""

from PySide6.QtGui import QPixmap

from typing import Dict

class CoverCache:
    cache: Dict[str, QPixmap] = {}
    