from PySide6.QtWidgets import QVBoxLayout, QSizePolicy, QFileDialog
from PySide6.QtGui import QImage, QPixmap
from PySide6.QtCore import Qt, QSize

from qfluentwidgets import PushButton, FluentIcon

from gui.component.widget.label import ImageLabel
from gui.component.dialog import FluentWidget

from util.network.request import NetworkRequestWorker, ResponseType
from util.thread.async_ import AsyncTask

import logging

logger = logging.getLogger(__name__)

class ViewCoverDialog(FluentWidget):
    def __init__(self, cover_url: str, parent = None):
        super().__init__(parent_window = parent)

        self.setWindowTitle(self.tr("Cover"))
        self.resize(650, 360)

        self.cover_url = cover_url
        self.cover_pixmap = None

        # 上一次缩放的目标物理尺寸。resizeEvent 会连续触发，每次都从原图重做一遍
        # 全量平滑下采样的话，拖拽缩放窗口会明显卡顿
        self._scaled_target = None

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

        if not image.loadFromData(data):
            # 失败时若静默 return，界面上只会一直停在加载动画里，无从判断原因
            logger.error("封面数据无法解码：%s", self.cover_url)

            self.image_lab.stop()

            return

        self.cover_pixmap = QPixmap.fromImage(image)
        self.image_lab.stop()

        self._scaled_target = None

        self._update_cover_pixmap()

    def _update_cover_pixmap(self):
        if not hasattr(self, 'cover_pixmap') or self.cover_pixmap is None or self.cover_pixmap.isNull():
            return

        # 按设备像素缩放：这个对话框存在的意义就是「把封面看清楚」，只按逻辑尺寸缩的话，
        # 高 DPI 屏上还要被绘制管线放大一次，等于白缩
        ratio = self.devicePixelRatioF()
        label_size = self.image_lab.size()

        target = QSize(round(label_size.width() * ratio), round(label_size.height() * ratio))

        if target == self._scaled_target:
            return

        self._scaled_target = target

        scaled = self.cover_pixmap.scaled(
            target,
            Qt.AspectRatioMode.KeepAspectRatio,
            Qt.TransformationMode.SmoothTransformation,
        )

        # 位图是物理像素尺寸，必须标注比例，否则 QLabel 会按位图自身的尺寸摆放，
        # 图片会显示成放大一倍多的样子
        scaled.setDevicePixelRatio(ratio)

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
