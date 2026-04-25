from PySide6.QtCore import QObject, Signal, QSize, Qt, QTimer
from PySide6.QtGui import QPixmap

from util.network import NetworkRequestWorker
from util.common.enum import QRCodeScanStatus
from util.thread import AsyncTask
from .base import AuthBase

from urllib.parse import urlencode
from qrcode import make as make_qrcode

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

    def generate(self):
        def on_success(response: dict):
            if self._cleaned_up:
                return

            self.check_response(response)

            self.qrcode_url = response["data"]["url"]
            self.qrcode_key = response["data"]["qrcode_key"]

            qrcode_image = make_qrcode(self.qrcode_url)

            pixmap = QPixmap.fromImage(qrcode_image.toqimage())
            pixmap = pixmap.scaled(QSize(160, 160), Qt.AspectRatioMode.KeepAspectRatio, Qt.TransformationMode.SmoothTransformation)

            self.qrcode_generated.emit(pixmap)

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
