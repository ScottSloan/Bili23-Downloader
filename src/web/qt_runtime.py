"""
按需拉起一个 offscreen 的 QGuiApplication

WebUI 进程原则上不碰 Qt，但有**一个例外**：ASS 弹幕的轨道排布要知道每条弹幕的像素宽度，
`QFontMetrics` 是目前唯一现成的字体度量来源（见 `parse/additional/file/danmaku_ass.py`，
它是 core 里唯一刻意保留 Qt 的文件）。

所以这里是惰性的：**只有真的要生成 ASS 弹幕时才会走到**，进程启动路径上一个 Qt 模块都不加载
（`test/web_entry.py` 盯着这一点）。

三条实测出来的约束：

- `QCoreApplication` **不够** —— 那样构造 QFontMetrics 会让进程直接崩溃，连异常都没有。
  必须是 QGuiApplication（QtWidgets 的 QApplication 更重，没必要）
- **不能跑它的事件循环**（D16）。只构造实例，不 `exec()`；实测与 asyncio 完全共存，
  循环照常调度
- **只能在主线程构造**。asyncio 循环已经在跑的时候构造也没问题（实测过），
  但从工作线程构造是 Qt 不支持的用法。构造完之后，工作线程使用 QFontMetrics 是安全的
  —— 这一点同样实测过

容器里还得装 CJK 字体，否则度量会落到 fallback 字体上，排出来的轨道会偏。
"""

from typing import Optional
import logging
import os
import sys
import threading

logger = logging.getLogger(__name__)

_checked = False
_available = False

def gui_application_available() -> bool:
    """已经建好了吗。不触发任何构造，纯查询"""
    return _available

def ensure_gui_application() -> bool:
    """
    确保进程里有一个 QGuiApplication，返回是否可用

    **必须从主线程调用。** 在工作线程里调用时，若实例尚未建立则直接返回 False 而不去构造 ——
    构造出来的是一个跨线程的 Qt 应用对象，后果比拿不到字体度量严重得多
    """
    global _checked, _available

    if _available:
        return True

    if threading.current_thread() is not threading.main_thread():
        # 已经建好的话上面就返回了，走到这里说明还没建，而这里建不了
        logger.error("QGuiApplication 只能在主线程建立，当前在 %s",
                     threading.current_thread().name)

        return False

    if _checked:
        # 上次就没建成（多半是没装 PySide6），不必每次都重试一遍导入
        return False

    _checked = True

    # offscreen：容器里没有 X11 / Wayland，不这么设的话构造会直接失败
    os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

    try:
        from PySide6.QtGui import QGuiApplication

    except ImportError as e:
        logger.warning("未安装 PySide6，ASS 弹幕不可用：%s", e)

        return False

    try:
        # 只传 argv[0]：真实的命令行里有 --web-ui、--port 这些，
        # Qt 会把认得的部分当成自己的参数吃掉
        instance = QGuiApplication.instance() or QGuiApplication(sys.argv[:1])

    except Exception:
        logger.exception("建立 QGuiApplication 失败，ASS 弹幕不可用")

        return False

    _available = True

    logger.info("已建立 offscreen QGuiApplication（仅用于 ASS 弹幕的字体度量，不跑事件循环）")

    return bool(instance)
