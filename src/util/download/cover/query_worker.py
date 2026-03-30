from PySide6.QtCore import QRunnable, Qt, QBuffer, QMetaObject, Q_ARG
from PySide6.QtGui import QPixmap

from util.network.request import NetworkRequestWorker, ResponseType
from util.thread import SyncTask

import base64

class CoverCache:
    cache: dict[str, QPixmap] = {}

class QueryWorker(QRunnable):
    def __init__(self, model, cover_id: str, cover_url: str):
        super().__init__()
    
        self.model = model
        self.cover_id = cover_id
        self.cover_url = cover_url

    def run(self):
        from util.download.cover.manager import cover_manager

        result = cover_manager.query(self.cover_id)

        if result:
            pixmap = QPixmap()
            pixmap.loadFromData(base64.b64decode(result))

        else:
            pixmap, base64_data = self.download_cover()

            cover_manager.create(self.cover_id, base64_data)

        cover_manager.updateCache(self.cover_id, pixmap)

        self.return_to_model()

    def return_to_model(self):
        QMetaObject.invokeMethod(
            self.model,
            "updateRowCover",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, self.cover_id)
        )

    def download_cover(self):
        def on_success(response: bytes):
            nonlocal pixmap

            pixmap = QPixmap()
            pixmap.loadFromData(response)

        pixmap = None

        # 数据库中没有封面数据，下载封面图片
        worker = NetworkRequestWorker(self.cover_url, response_type = ResponseType.BYTES)
        worker.success.connect(on_success)

        SyncTask.run(worker)

        return self.process_cover(pixmap)
        
    def process_cover(self, pixmap: QPixmap):
        # 裁剪成 16:9，并缩放到 144x81
        width = 144
        height = 81

        pixmap: QPixmap = pixmap.scaled(width, height, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)

        pixmap = pixmap.copy((pixmap.width() - width) // 2, (pixmap.height() - height) // 2, width, height)

        # 导出为 webp 格式的 base64，最大化压缩率以节省数据库空间
        buffer = QBuffer()
        buffer.open(QBuffer.OpenModeFlag.WriteOnly)
        pixmap.save(buffer, "WEBP")

        base64_data = base64.b64encode(buffer.data()).decode("utf-8")

        return pixmap, base64_data
