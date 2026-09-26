from PySide6.QtGui import QPixmap

from typing import ClassVar
from collections import OrderedDict

class CoverCache:
    # 用 OrderedDict 维护访问顺序：getCache 命中时把条目移到末尾，写入超出上限时从头部淘汰，
    # 合起来就是 LRU。封面按设备像素存放，单张上百 KB，没有上限时列表滚动会持续累积
    cache: ClassVar[OrderedDict[str, QPixmap]] = OrderedDict()
    