from PySide6.QtWidgets import QVBoxLayout, QSizePolicy, QFileDialog
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import Qt, QRect

from qfluentwidgets import PushButton, FluentIcon

from gui.component.widget.label import ImageLabel
from gui.component.dialog import FluentWidget

from util.network.request import NetworkRequestWorker, ResponseType
from util.thread.async_ import AsyncTask

class ViewCoverDialog(FluentWidget):
    def __init__(self, cover_url: str, parent = None):
        super().__init__(parent)

        self.setWindowTitle(self.tr("Cover"))
        self.resize(650, 360)

        self.cover_url = cover_url
        self.cover_pixmap = None

        self.init_UI()

        self._init_common()

        self.load_cover()

    def init_UI(self):
        self.save_as_btn = PushButton(self.tr("Save As"), parent = self)
        self.save_as_btn.setIcon(FluentIcon.SAVE)
        self.save_as_btn.setFixedSize(120, 30)
        self.save_as_btn.clicked.connect(self.on_save_as)

        self.image_lab = ImageLabel(parent = self)
        self.image_lab.setAlignment(Qt.AlignmentFlag.AlignCenter)
        self.image_lab.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.image_lab.resize(640, 340)
        self.image_lab.loading()

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(10, self.titleBar.height(), 10, 10)
        main_layout.addWidget(self.save_as_btn)
        main_layout.addWidget(self.image_lab, 1)

    def load_cover(self):
        worker = NetworkRequestWorker(url = self.cover_url, response_type = ResponseType.BYTES)
        worker.success.connect(self.on_load_success)

        AsyncTask.run(worker)

    def on_load_success(self, data: bytes):
        image = QImage()
        image.loadFromData(data)

        self.cover_pixmap = QPixmap.fromImage(image)
        self.image_lab.stop()

        self._update_cover_pixmap()

    def _update_cover_pixmap(self):
        if not hasattr(self, 'cover_pixmap') or self.cover_pixmap is None or self.cover_pixmap.isNull():
            return

        scaled = self.cover_pixmap.scaled(
            self.image_lab.size(),
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )
        self.image_lab.setPixmap(scaled)

    def resizeEvent(self, event):
        self._update_cover_pixmap()

        return super().resizeEvent(event)
    
    def on_save_as(self):
        dialog = QFileDialog(
            self, self.tr("Save As"),
            filter = self.tr("JPEG Image (*.jpg);;PNG Image (*.png);;WebP Image (*.webp)"),
            acceptMode = QFileDialog.AcceptMode.AcceptSave
        )

        if dialog.exec() == QFileDialog.DialogCode.Accepted:
            file_path = dialog.selectedFiles()[0]
            format = dialog.selectedNameFilter().split("(*.")[1].rstrip(")")

            self.cover_pixmap.save(file_path, format = format)
