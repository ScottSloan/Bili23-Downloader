from PySide6.QtCore import QObject, Signal, QSize, Qt, QTimer
from PySide6.QtGui import QImage, QPainter, QPixmap

from ..network.request import NetworkRequestWorker
from ..common.enum import QRCodeScanStatus
from ..thread.async_ import AsyncTask
from .base import AuthBase

from qrcode import QRCode as QRCodeGenerator
from urllib.parse import urlencode

class QRCode(AuthBase, QObject):
    qrcode_generated = Signal(QPixmap)
    update_scan_status = Signal(int)

    error = Signal(str)

    def __init__(self, parent = None):
        AuthBase.__init__(self)
        QObject.__init__(self, parent)

        self._cleaned_up = False

        self.qrcode_url = ""
        self.qrcode_key = ""

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
        def on_success(response: dict):
            if self._cleaned_up:
                return

            self.check_response(response)

            self.qrcode_url = response["data"]["url"]
            self.qrcode_key = response["data"]["qrcode_key"]

            self.qrcode_generated.emit(self._build_qrcode_pixmap(self.qrcode_url))

        params = {
            "source": "main-fe-header",
            "go_url": "https://www.bilibili.com/",
            "web_location": "333.1007"
        }

        url = f"https://passport.bilibili.com/x/passport-login/web/qrcode/generate?{urlencode(params)}"

        worker = NetworkRequestWorker(url)
        worker.success.connect(on_success)
        worker.error.connect(self.on_error)

        AsyncTask.run(worker)

    def check_scan_status(self):
        def on_success(response: dict):
            if self._cleaned_up:
                return

            self.check_response(response)

            code = response["data"]["code"]

            if code == QRCodeScanStatus.SUCCESS:
                self.update_cookies()

            if self.timer.isActive():
                self.update_scan_status.emit(code)

        url = f"https://passport.bilibili.com/x/passport-login/web/qrcode/poll?qrcode_key={self.qrcode_key}"

        worker = NetworkRequestWorker(url)
        worker.success.connect(on_success)
        worker.error.connect(self.on_error)

        AsyncTask.run(worker)

    def start_polling(self):
        self.timer.start(1000)

    def stop_polling(self):
        self.timer.stop()
