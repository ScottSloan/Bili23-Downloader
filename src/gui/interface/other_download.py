"""
其他视频下载页面

处理非 B 站来源的直接视频 URL 下载。
"""

from PySide6.QtWidgets import QFrame, QVBoxLayout
from PySide6.QtCore import Qt

from qfluentwidgets import LineEdit, PrimaryPushButton, BodyLabel

from util.common.enum import ToastNotificationCategory
from util.common.signal_bus import signal_bus


class OtherDownloadInterface(QFrame):
    """其他视频下载页面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("OtherDownloadInterface")

        self.init_UI()

    def init_UI(self):
        url_label = BodyLabel(self.tr("Video URL:"), self)
        self.url_input = LineEdit(self)
        self.url_input.setPlaceholderText(self.tr("Enter any downloadable video URL…"))
        self.url_input.setClearButtonEnabled(True)

        self.download_btn = PrimaryPushButton(self.tr("Download"), self)

        hint_label = BodyLabel(
            self.tr("Supports direct download links. If the link cannot be downloaded, an error will be shown."),
            self
        )
        hint_label.setWordWrap(True)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(30, 30, 30, 30)

        layout.addWidget(url_label)
        layout.addWidget(self.url_input)
        layout.addSpacing(15)
        layout.addWidget(self.download_btn, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addSpacing(20)
        layout.addWidget(hint_label)
        layout.addStretch(1)

        self.download_btn.clicked.connect(self._on_download)

    def _on_download(self):
        url = self.url_input.text().strip()
        if not url:
            signal_bus.toast.show.emit(
                ToastNotificationCategory.WARNING,
                self.tr("Input Required"),
                self.tr("Please enter a video URL.")
            )
            return

        # 直接 URL 下载：添加到现有下载队列
        from util.download.task.info import TaskInfo
        from util.common.enum import DownloadStatus

        try:
            task_info = TaskInfo()
            task_info.Episode.url = url
            task_info.File.name = url.rsplit("/", 1)[-1].split("?")[0] or "download"
            task_info.Download.status = DownloadStatus.QUEUED

            signal_bus.download.create_task.emit([task_info])

            self.url_input.clear()

            signal_bus.toast.show.emit(
                ToastNotificationCategory.SUCCESS,
                self.tr("Task Created"),
                self.tr("Download task has been added to the download list.")
            )
        except Exception as e:
            signal_bus.toast.show.emit(
                ToastNotificationCategory.ERROR,
                self.tr("Download Failed"),
                str(e)
            )
