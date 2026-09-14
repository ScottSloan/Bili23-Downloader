from PySide6.QtGui import QPixmap

from typing import ClassVar

class CoverCache:
    cache: ClassVar[dict[str, QPixmap]] = {}
    