from PySide6.QtCore import QRunnable, Qt, QBuffer, QMetaObject, Q_ARG, QSize
from PySide6.QtGui import QImage

from shiboken6 import isValid

from ...network.request import SyncNetWorkRequest, ResponseType

from urllib.parse import urlencode
import logging

# 不在模块顶层导入 httpx：本模块经封面列表被界面模块间接引入，而导入 httpx
# 需要连带加载 httpcore、ssl 等约 40 个模块（实测 64ms）。main.py 特意把网络栈
# 预热放到后台线程，若此处在顶层导入，这笔开销就又回到了 GUI 线程上 ——
# init_deferred_ui 比 warmup_network_stack 先执行（零延时定时器按注册顺序触发）

logger = logging.getLogger(__name__)

class CoverQueryWorker(QRunnable):
    def __init__(self, model, cover_key: str, cover_url: str, cover_size: QSize, query_param: dict = None):
        super().__init__()
    
        self.model = model

        # 缓存键，同时用作回报模型时的标识
        self.cover_key = cover_key

        self.cover_url = cover_url
        self.cover_size = cover_size

        self.query_param = query_param

    def run(self):
        try:
            self._run()

        except Exception:
            logger.exception("加载封面失败：%s", self.cover_url)

            self.notify_failed()

    def _run(self):
        if self.query_param:
            try:
                self.query_url()

            except Exception:
                # 查询失败则无法继续后续流程。这里必须留痕：
                # 否则界面上只表现为「没有封面」，无从判断是网络问题还是接口变更
                logger.exception("查询封面 URL 失败")

                self.notify_failed()

                return

        if not self.cover_url:
            # 会员购商城课程等条目的接口不返回封面，无需请求。
            # 刻意不回报失败：它本来就没有封面，回报会让模型释放等待集合，
            # 于是每次重绘都重新发起一次注定失败的请求
            return

        image = self.query_cache()

        if image is None:
            image = self.download_and_cache()

        self.return_to_model(image)

    def query_cache(self):
        from ..cover.manager import cover_manager

        # 返回 None 表示缓存未命中或数据已损坏，需要重新下载
        result = cover_manager.query(self.cover_key)

        if not result:
            return None

        # 更早的版本把封面以 base64 文本存进这一列，格式迁移会清空它们。
        # 万一有残留，这里挡下来当作未命中重新下载，避免把 str 交给 loadFromData
        if not isinstance(result, bytes):
            logger.warning("封面缓存格式已过期，将重新下载：%s", self.cover_url)

            return None

        image = QImage()

        if not image.loadFromData(result):
            # 历史脏数据（例如 CDN 的错误页被原样存了进来）。留痕：
            # 这种行查询出来是空值，界面上只表现为「这个封面永远加载不出来」
            logger.warning("封面缓存无法解码，将重新下载：%s", self.cover_url)

            return None

        return image

    def download_and_cache(self):
        import httpx

        for attempt in range(3):
            try:
                image, cover_data = self.download_cover()
                break

            except httpx.HTTPError:
                # 只重试网络错误。解码失败（ValueError）重试同一张坏图没有意义
                if attempt == 2:
                    raise

        self.save_cache(cover_data)

        return image

    def save_cache(self, cover_data: bytes):
        from ..cover.manager import cover_manager

        try:
            cover_manager.create(self.cover_key, cover_data)

        except Exception:
            # 写缓存只是展示路径上的尽力而为：数据库故障不该让已经拿到手的封面显示不出来
            logger.exception("写入封面缓存失败：%s", self.cover_url)

    def return_to_model(self, image: QImage):
        # 封面请求耗时可达数秒，期间界面可能已被销毁，
        # 向一个 C++ 侧已析构的 QObject 投递调用会直接触发访问违例
        if self.model is None or not isValid(self.model):
            return

        QMetaObject.invokeMethod(
            self.model,
            "updateRowCover",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, self.cover_key),
            Q_ARG(QImage, image)
        )

    def notify_failed(self):
        # 必须回报失败：模型侧靠它释放等待集合，否则这个封面在这个列表里再也不会被请求，
        # 表现为永远空着 —— 连滚动重绘都不会重新触发
        if self.model is None or not isValid(self.model):
            return

        QMetaObject.invokeMethod(
            self.model,
            "onCoverFailed",
            Qt.ConnectionType.QueuedConnection,
            Q_ARG(str, self.cover_key)
        )

    def download_cover(self):
        # 数据库中没有封面数据，下载封面图片
        request = SyncNetWorkRequest(self.cover_url, response_type = ResponseType.BYTES)
        response = request.run()

        image = QImage()

        # 非图片的 200 响应（CDN 错误页、拦截页）此前会一路静默传下去：
        # 产出空数据写进缓存，且全程既不抛异常也不留日志
        if not image.loadFromData(response):
            raise ValueError("封面数据无法解码")

        return self.process_cover(image)
        
    def process_cover(self, image: QImage):
        # 裁剪成 16:9，并缩放到物理像素尺寸（由模型侧按设备像素比算出）
        width = self.cover_size.width()
        height = self.cover_size.height()

        image: QImage = image.scaled(width, height, Qt.AspectRatioMode.KeepAspectRatioByExpanding, Qt.TransformationMode.SmoothTransformation)

        image = image.copy((image.width() - width) // 2, (image.height() - height) // 2, width, height)

        # 导出为 webp，最大化压缩率以节省数据库空间。
        # 质量取 90：Qt 默认的 75 在封面这种尺寸的图上会让边缘和细节发糊，
        # 而尺寸已按设备像素取到刚好，压缩损失不再有放大来掩盖，会原样显示出来
        buffer = QBuffer()
        buffer.open(QBuffer.OpenModeFlag.WriteOnly)

        if not image.save(buffer, "WEBP", 90):
            # 保存失败会写出空数据，写进缓存就是一行永远命不中的脏数据
            raise ValueError("封面编码为 webp 失败")

        # 直接存 webp 原始字节。早先存的是 base64 文本，平白多占 33% 体积，
        # 写入与读取还各要多做一次编解码
        return image, bytes(buffer.data())

    def query_url(self):
        from ..cover.manager import cover_manager

        api_url = self.query_param.get("api_url")
        params = self.query_param.get("params")
        
        url = f"{api_url}?{urlencode(params)}"

        request = SyncNetWorkRequest(url)
        response = request.run()

        cover_url = response.get("data", {}).get("cover", "")

        if not cover_url:
            raise ValueError("获取封面 URL 失败")

        # 换成真实封面 URL 对应的 cover_id，但尺寸后缀必须保留 —— 模型侧是按
        # 「cover_id@宽x高」请求的，写回裸 md5 就永远对不上，缓存永不命中
        self.cover_key = cover_manager.arrange_cover_key(cover_manager.arrange_cover_id(cover_url), self.cover_size)
        self.cover_url = cover_url
