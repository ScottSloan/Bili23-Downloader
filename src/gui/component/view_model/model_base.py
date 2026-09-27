from PySide6.QtCore import QAbstractListModel, Slot, QSize
from PySide6.QtGui import QImage, QPixmap

from util.download.cover.manager import cover_manager

from typing import Dict, Set

class CoverQueryModelBase(QAbstractListModel):
    """
    具有异步封面显示功能的模型基类
    """

    def __init__(self, parent = None):
        super().__init__(parent)

        # 存放的必须是逻辑尺寸。封面实际按「逻辑尺寸 × 设备像素比」生成与存取，
        # 由 cover_pixel_size() 派生。若这里改成物理尺寸，绘制阶段会把它再放大一次，
        # 变成先放大再缩小的双重劣化
        self._cover_size = QSize(120, 67)
        self.cover_waiting_rows: Dict[str, Set[int]] = {}

        self.query_param = None
    
    def cover_pixel_size(self, device_pixel_ratio: float) -> QSize:
        """封面在缓存与数据库中的尺寸，按设备像素取

        绘制时是把整张位图铺满封面矩形，若只按逻辑尺寸存取，高 DPI 屏上就要由绘制
        管线放大 —— DPR 1.5 实测 PSNR 掉 7dB，而且是每次重绘都在发生的持续模糊。

        尺寸与目标设备像素精确相等时最优。不要改成固定 2 倍：288x160 送到 216x120
        的设备矩形上是 4/3 的非整数倍下采样，正好落在 Qt 双线性重采样的弱项上，
        实测反而比 216x120 更差。这里按实际比例取，让绘制恰好 1:1。
        """
        return QSize(
            round(self._cover_size.width() * device_pixel_ratio),
            round(self._cover_size.height() * device_pixel_ratio)
        )

    def queryRowCover(self, cover_id: str, cover_url: str, row: int, device_pixel_ratio: float) -> tuple[QPixmap, bool]:
        # 由委托发起查询封面请求
        query_param = None

        pixel_size = self.cover_pixel_size(device_pixel_ratio)

        if cover_id is None:
            return cover_manager.placeholder(pixel_size), True
        
        elif cover_id.startswith("__query__"):
            # 需要通过封面 URL 查询封面 URL 的特殊情况，由委托传入 query_param 进行查询，此时 cover_url 作为查询参数传入
            query_param = self.query_param.copy()
            query_param["params"] = {
                "media_id": cover_url
            }
        
        cover_key = cover_manager.arrange_cover_key(cover_id, pixel_size)

        # 命中缓存，直接返回
        if cahce := cover_manager.getCache(cover_key):
            return cahce, False

        # 记录等待该 cover_key 的所有 row
        waiting_set = self.cover_waiting_rows.setdefault(cover_key, set())

        if row not in waiting_set:
            waiting_set.add(row)

            # 只在首次请求时启动worker
            if len(waiting_set) == 1:
                cover_manager.request(self, cover_key, cover_url, pixel_size, query_param)

        return cover_manager.placeholder(pixel_size), True

    @Slot(str, QImage)
    def updateRowCover(self, cover_key: str, image: QImage):
        # 缓存图片（回到 GUI 线程后再转成 QPixmap）
        pixmap = QPixmap.fromImage(image)
        cover_manager.updateCache(cover_key, pixmap)

        self._release_waiting_rows(cover_key, refresh = True)

    @Slot(str)
    def onCoverFailed(self, cover_key: str):
        # 加载失败时也要释放等待集合，否则该条目会一直留着，
        # 使得这个封面在这个列表里再也不会被请求 —— 表现为永远空着，滚动重绘也不会重试
        self._release_waiting_rows(cover_key, refresh = False)

    def _release_waiting_rows(self, cover_key: str, refresh: bool):
        if cover_key not in self.cover_waiting_rows:
            return

        if refresh:
            for row in self.cover_waiting_rows[cover_key]:
                index = self.index(row)

                # 封面请求耗时可达数秒，期间列表可能已经增删过，记下的行号会失效。
                # dataChanged 要求索引有效，传入无效索引会让视图与代理模型按 -1 去取行
                if not index.isValid():
                    continue

                self.dataChanged.emit(index, index)

        # 失败路径绝不能刷新：重绘会重新发起请求，请求又失败又会走到这里，
        # 就成了「重绘 → 请求 → 失败 → 重绘」的死循环
        del self.cover_waiting_rows[cover_key]

    def setQueryCoverParam(self, param: dict):
        self.query_param = param
