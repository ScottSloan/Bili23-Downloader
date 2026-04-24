from PySide6.QtCore import QRunnable, Qt, QBuffer, QMetaObject, Q_ARG, QSize
from PySide6.QtGui import QImage

from util.network import SyncNetWorkRequest, ResponseType

from urllib.parse import urlencode
import base64
import httpx

class CoverQueryWorker(QRunnable):
    def __init__(self, model, query_id: str, cover_id: str, cover_url: str, cover_size: QSize, query_param: dict = None):
        super().__init__()
    
        self.model = model
        self.query_id = query_id
        self.cover_id = cover_id

        self.cover_url = cover_url
        self.cover_size = cover_size

        self.query_param = query_param

    def run(self):
        from util.download.cover.manager import cover_manager

        if self.query_param:
            try:
                self.query_url()

            except Exception:
                # 查询封面 URL 失败，无法继续后续流程
                return

        result = cover_manager.query(self.cover_id)

        if result:
            image = QImage()
            image.loadFromData(base64.b64decode(result))

        else:
            for i in range(3):
                try:
                    image, base64_data = self.download_cover()
                    break
                except httpx.HTTPError:
                    if i == 2:
                        raise
            else:
                return
            
            cover_manager.create(self.cover_id, base64_data)

        self.return_to_model(image)

    def return_to_model(self, image: QImage):
        QMetaObject.invokeMethod(
            self.model,
            "updateRowCover",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, self.query_id),
            Q_ARG(QImage, image)
        )

    def download_cover(self):
        # 数据库中没有封面数据，下载封面图片
        request = SyncNetWorkRequest(self.cover_url, response_type = ResponseType.BYTES)
        response = request.run()

        image = QImage()
        image.loadFromData(response)

        return self.process_cover(image)
        
    def process_cover(self, image: QImage):
        # 裁剪成 16:9，并缩放到 144x81
        width = self.cover_size.width()
        height = self.cover_size.height()

        image: QImage = image.scaled(width, height, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)

        image = image.copy((image.width() - width) // 2, (image.height() - height) // 2, width, height)

        # 导出为 webp 格式的 base64，最大化压缩率以节省数据库空间
        buffer = QBuffer()
        buffer.open(QBuffer.OpenModeFlag.WriteOnly)
        image.save(buffer, "WEBP")

        base64_data = base64.b64encode(buffer.data()).decode("utf-8")

        return image, base64_data

    def query_url(self):
        from util.download.cover.manager import cover_manager

        api_url = self.query_param.get("api_url")
        params = self.query_param.get("params")
        
        url = f"{api_url}?{urlencode(params)}"

        request = SyncNetWorkRequest(url)
        response = request.run()

        cover_url = response.get("data", {}).get("cover", "")

        if not cover_url:
            raise ValueError("获取封面 URL 失败")

        self.cover_id = cover_manager.arrange_cover_id(cover_url)
        self.cover_url = cover_url
