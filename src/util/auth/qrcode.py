from PySide6.QtCore import QObject, Signal, Slot, QSize, Qt, QTimer
from PySide6.QtGui import QImage, QPainter, QPixmap

from ..network.worker import NetworkRequestWorker
from ..thread.async_ import AsyncTask
from .base import AuthBase
from .qrcode_session import QRCodeSession, generate_url, poll_url

from qrcode import QRCode as QRCodeGenerator

class QRCode(AuthBase, QObject):
    """
    桌面侧的扫码登录

    **拼 URL、校验响应、写回 Cookie 都在 `qrcode_session.py` 里，与 WebUI 共用一份。**
    这里只保留桌面特有的三样：QTimer 轮询、QPixmap 出图、Qt 信号回调 ——
    前两样在没有 Qt 事件循环的进程里用不了，第三样服务端也不需要
    """

    qrcode_generated = Signal(QPixmap)
    update_scan_status = Signal(int)

    error = Signal(str)

    def __init__(self, parent = None):
        AuthBase.__init__(self)
        QObject.__init__(self, parent)

        self._cleaned_up = False

        # 请求与响应处理都交给它，本类只管界面这一侧
        self.session = QRCodeSession()
        # 把 session 的报错接回本对象：这样错误提示仍走桌面那条路，
        # 而且 cleanup 之后的迟到错误会被这里的 _cleaned_up 判断挡掉
        self.session.on_error = self.on_error

        self.timer = QTimer(self)
        self.timer.timeout.connect(self.check_scan_status)

    def cleanup(self):
        self._cleaned_up = True

        self.stop_polling()

        try:
            self.timer.timeout.disconnect(self.check_scan_status)
        except Exception:
            pass

    def on_error(self, message: str):
        if self._cleaned_up:
            return

        super().on_error(message)

    def _build_qrcode_pixmap(self, data: str) -> QPixmap:
        # 生成 QR 码矩阵
        qr_code = QRCodeGenerator(border = 4)
        qr_code.add_data(data)
        qr_code.make(fit=True)

        matrix = qr_code.get_matrix()
        module_count = len(matrix)
        box_size = max(1, 160 // module_count)
        image_size = module_count * box_size

        image = QImage(image_size, image_size, QImage.Format.Format_ARGB32)
        image.fill(Qt.GlobalColor.white)

        painter = QPainter(image)
        try:
            painter.setPen(Qt.PenStyle.NoPen)
            painter.setBrush(Qt.GlobalColor.black)

            for row_index, row in enumerate(matrix):
                y = row_index * box_size

                for column_index, is_dark in enumerate(row):
                    if is_dark:
                        painter.drawRect(column_index * box_size, y, box_size, box_size)
        finally:
            painter.end()

        return QPixmap.fromImage(image).scaled(
            QSize(160, 160),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

    def generate(self):
        worker = NetworkRequestWorker(generate_url())
        # 连到本对象的方法而非闭包，Qt 会把回调排队回 GUI 线程：QPixmap 只能在 GUI 线程构造
        worker.success.connect(self.on_generate_success)
        worker.error.connect(self.on_error)

        AsyncTask.run(worker)

    @Slot(object)
    def on_generate_success(self, response: dict):
        if self._cleaned_up:
            return

        try:
            url, _ = self.session.parse_generate(response)

        except RuntimeError:
            # check_response 内部已经发出过 error 信号
            return

        self.qrcode_generated.emit(self._build_qrcode_pixmap(url))

    def check_scan_status(self):
        worker = NetworkRequestWorker(poll_url(self.qrcode_key))
        # 同上，回调里要访问 GUI 线程的 QTimer，必须由 Qt 排队回来
        worker.success.connect(self.on_poll_success)
        worker.error.connect(self.on_error)

        AsyncTask.run(worker)

    @Slot(object)
    def on_poll_success(self, response: dict):
        if self._cleaned_up:
            return

        try:
            code = self.session.parse_poll(response)

        except RuntimeError:
            return

        if self.timer.isActive():
            self.update_scan_status.emit(code)

    @property
    def qrcode_url(self):
        return self.session.qrcode_url

    @property
    def qrcode_key(self):
        return self.session.qrcode_key

    def start_polling(self):
        self.timer.start(1000)

    def stop_polling(self):
        self.timer.stop()
