from PySide6.QtGui import QPixmap

from typing import Dict

class CoverCache:
    cache: Dict[str, QPixmap] = {}
    