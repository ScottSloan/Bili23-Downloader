"""
AI 总结主界面模块

包含两个可切换子页面：
  - 子页面 1：B 站总结页（URL 输入 → 下载 → Cloudflare 总结）
  - 子页面 2：其他总结页（本地文件选择 → Cloudflare 总结）
"""

from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout, QFileDialog, QTextEdit, QWidget
from PySide6.QtCore import Qt

from qfluentwidgets import (
    Pivot, PopUpAniStackedWidget, LineEdit, ComboBox, PrimaryPushButton,
    BodyLabel,
)

from gui.component.widget.button import IndeterminateProgressPushButton

from util.common.data.aisum_models import (
    SummaryType, DEFAULT_MODELS, DEFAULT_MODEL_ID,
)
from util.common.config import config
from util.common.enum import ToastNotificationCategory
from util.common.signal_bus import signal_bus
from util.thread.async_ import AsyncTask
from util.aisum.worker import SummaryWorker, LocalFileSummaryWorker

import subprocess
import sys
import os


# ============================================================
# 子页面 1：B 站总结页
# ============================================================
class _BilibiliSumPage(QWidget):
    """B 站视频内容总结"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self.init_UI()

    def init_UI(self):
        url_label = BodyLabel(self.tr("Video URL / BV Number:"), self)
        self.url_input = LineEdit(self)
        self.url_input.setPlaceholderText(self.tr("Enter Bilibili video link or BV number…"))
        self.url_input.setClearButtonEnabled(True)

        type_label = BodyLabel(self.tr("Summary Type:"), self)
        self.type_combo = ComboBox(self)
        self.type_combo.addItems([
            SummaryType.SUBTITLE.value,
            SummaryType.VIDEO.value,
            SummaryType.AUDIO.value,
        ])

        model_label = BodyLabel(self.tr("Model:"), self)
        self.model_combo = ComboBox(self)
        for m in DEFAULT_MODELS:
            self.model_combo.addItem(m.display_name, userData=m.model_id)
        current_model = config.get(config.cloudflare_model) or DEFAULT_MODEL_ID
        for i in range(self.model_combo.count()):
            if self.model_combo.itemData(i) == current_model:
                self.model_combo.setCurrentIndex(i)
                break

        self.submit_btn = IndeterminateProgressPushButton(self.tr("Summarize"), self)

        # 结果区：三组 Show in Finder / Delete 按钮
        result_label = BodyLabel(self.tr("Results:"), self)
        self.result_widget = QWidget(self)
        self.result_layout = QVBoxLayout(self.result_widget)
        self.result_layout.setContentsMargins(0, 0, 0, 0)
        self.result_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._result_rows = []  # (QWidget, file_path)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(0, 0, 0, 0)

        main_layout.addWidget(url_label)
        main_layout.addWidget(self.url_input)
        main_layout.addSpacing(10)

        opts_layout = QHBoxLayout()
        opts_layout.addWidget(type_label)
        opts_layout.addWidget(self.type_combo)
        opts_layout.addSpacing(20)
        opts_layout.addWidget(model_label)
        opts_layout.addWidget(self.model_combo)
        opts_layout.addStretch()
        main_layout.addLayout(opts_layout)

        main_layout.addSpacing(10)
        main_layout.addWidget(self.submit_btn, 0, Qt.AlignmentFlag.AlignLeft)
        main_layout.addSpacing(15)
        main_layout.addWidget(result_label)
        main_layout.addWidget(self.result_widget)
        main_layout.addStretch(1)

        self.submit_btn.clicked.connect(self._on_submit)

    def _on_submit(self):
        url = self.url_input.text().strip()
        if not url:
            signal_bus.toast.show.emit(
                ToastNotificationCategory.WARNING,
                self.tr("Input Required"),
                self.tr("Please enter a Bilibili video URL or BV number.")
            )
            return

        summary_type = SummaryType(self.type_combo.currentText())

        model_idx = self.model_combo.currentIndex()
        if 0 <= model_idx < len(DEFAULT_MODELS):
            config.set(config.cloudflare_model, DEFAULT_MODELS[model_idx].model_id)

        self.submit_btn.setIndeterminateState(True)
        self._clear_results()

        self._worker = SummaryWorker(url, summary_type)
        self._worker.success.connect(self._on_success)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self._on_finished)

        AsyncTask.run(self._worker)

    def _on_success(self, json_path: str, organized_path: str, summary_path: str):
        if json_path:
            self._add_result_row(self.tr("Subtitle JSON"), json_path)
        if organized_path:
            self._add_result_row(self.tr("Organized Text"), organized_path)
        if summary_path:
            self._add_result_row(self.tr("AI Summary"), summary_path)

        signal_bus.toast.show.emit(
            ToastNotificationCategory.SUCCESS,
            self.tr("Summary Complete"),
            self.tr("Content summarization finished successfully.")
        )

    def _on_error(self, error_message: str):
        label = BodyLabel(error_message, self)
        self.result_layout.addWidget(label)
        signal_bus.toast.show.emit(
            ToastNotificationCategory.ERROR,
            self.tr("Summary Failed"),
            error_message
        )

    def _on_finished(self):
        self.submit_btn.setIndeterminateState(False)

    def _add_result_row(self, label_text: str, file_path: str):
        """添加一行：标签 | [Show in Finder] | [Delete]"""
        row = QWidget(self.result_widget)
        row_layout = QHBoxLayout(row)
        row_layout.setContentsMargins(0, 4, 0, 4)

        label = BodyLabel(label_text, row)
        show_btn = PrimaryPushButton(self.tr("Show in Finder"), row)
        delete_btn = PrimaryPushButton(self.tr("Delete"), row)

        show_btn.clicked.connect(lambda: _show_in_finder(file_path))
        delete_btn.clicked.connect(lambda: self._delete_file(row, file_path))

        row_layout.addWidget(label)
        row_layout.addStretch(1)
        row_layout.addWidget(show_btn)
        row_layout.addWidget(delete_btn)

        self.result_layout.addWidget(row)
        self._result_rows.append((row, file_path))

    def _delete_file(self, row: QWidget, file_path: str):
        try:
            Path = __import__("pathlib").Path
            p = Path(file_path)
            if p.exists():
                p.unlink()
        except Exception as e:
            signal_bus.toast.show.emit(
                ToastNotificationCategory.WARNING,
                self.tr("Delete Failed"),
                str(e)
            )
            return

        # 从 UI 中移除行
        self.result_layout.removeWidget(row)
        row.deleteLater()
        self._result_rows = [(r, f) for r, f in self._result_rows if f != file_path]

        signal_bus.toast.show.emit(
            ToastNotificationCategory.SUCCESS,
            self.tr("Deleted"),
            self.tr("File has been deleted.")
        )

    def _clear_results(self):
        """清空所有结果行"""
        for row, _ in self._result_rows:
            self.result_layout.removeWidget(row)
            row.deleteLater()
        self._result_rows = []


# ============================================================
# 子页面 2：其他总结页（本地文件）
# ============================================================
class _OtherSumPage(QWidget):
    """本地文件内容总结"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self.init_UI()

    def init_UI(self):
        file_label = BodyLabel(self.tr("Select File:"), self)

        file_row = QWidget(self)
        file_layout = QHBoxLayout(file_row)
        file_layout.setContentsMargins(0, 0, 0, 0)

        self.file_path_input = LineEdit(self)
        self.file_path_input.setPlaceholderText(self.tr("Select local file..."))
        self.file_path_input.setReadOnly(True)
        self.file_path_input.setClearButtonEnabled(True)

        browse_btn = PrimaryPushButton(self.tr("Browse"), self)
        browse_btn.clicked.connect(self._browse_file)

        file_layout.addWidget(self.file_path_input, 1)
        file_layout.addWidget(browse_btn)

        type_label = BodyLabel(self.tr("Content Type:"), self)
        self.type_combo = ComboBox(self)
        self.type_combo.addItems([
            SummaryType.SUBTITLE.value,
            SummaryType.AUDIO.value,
            SummaryType.VIDEO.value,
        ])

        self.submit_btn = IndeterminateProgressPushButton(self.tr("Summarize"), self)

        result_label = BodyLabel(self.tr("Result:"), self)
        self.result_text = QTextEdit(self)
        self.result_text.setReadOnly(True)
        self.result_text.setPlaceholderText(self.tr("Summary result will be displayed here…"))

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)

        layout.addWidget(file_label)
        layout.addWidget(file_row)
        layout.addSpacing(10)

        opts_layout = QHBoxLayout()
        opts_layout.addWidget(type_label)
        opts_layout.addWidget(self.type_combo)
        opts_layout.addStretch()
        layout.addLayout(opts_layout)

        layout.addSpacing(10)
        layout.addWidget(self.submit_btn, 0, Qt.AlignmentFlag.AlignLeft)
        layout.addSpacing(15)
        layout.addWidget(result_label)
        layout.addWidget(self.result_text, 1)

        self.submit_btn.clicked.connect(self._on_submit)

    def _browse_file(self):
        path, _ = QFileDialog.getOpenFileName(
            self,
            self.tr("Select File"),
            "",
            self.tr(
                "All Supported (*.json *.txt *.srt *.ass *.vtt *.mp3 *.m4a *.wav "
                "*.mp4 *.mkv *.flv *.aac *.ogg *.flac *.xml);;All Files (*)"
            ),
        )
        if path:
            self.file_path_input.setText(path)

    def _on_submit(self):
        from pathlib import Path

        file_path = self.file_path_input.text().strip()
        if not file_path:
            signal_bus.toast.show.emit(
                ToastNotificationCategory.WARNING,
                self.tr("No File Selected"),
                self.tr("Please select a local file first.")
            )
            return

        if not Path(file_path).exists():
            signal_bus.toast.show.emit(
                ToastNotificationCategory.ERROR,
                self.tr("File Not Found"),
                self.tr("The selected file does not exist.")
            )
            return

        summary_type = SummaryType(self.type_combo.currentText())

        self.submit_btn.setIndeterminateState(True)
        self.result_text.clear()

        self._worker = LocalFileSummaryWorker(file_path, summary_type)
        self._worker.success.connect(self._on_success)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self._on_finished)

        AsyncTask.run(self._worker)

    def _on_success(self, result: str):
        self.result_text.setPlainText(result)
        signal_bus.toast.show.emit(
            ToastNotificationCategory.SUCCESS,
            self.tr("Summary Complete"),
            self.tr("Content summarization finished successfully.")
        )

    def _on_error(self, error_message: str):
        self.result_text.setPlainText(error_message)
        signal_bus.toast.show.emit(
            ToastNotificationCategory.ERROR,
            self.tr("Summary Failed"),
            error_message
        )

    def _on_finished(self):
        self.submit_btn.setIndeterminateState(False)


# ============================================================
# AISum 主界面（Pivot 容器）
# ============================================================
class AISumInterface(QFrame):
    """AI 总结主界面"""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AISumInterface")

        self.pivot = Pivot(self)

        self.bilibili_page = _BilibiliSumPage(self)
        self.other_page = _OtherSumPage(self)

        self.stacked_widget = PopUpAniStackedWidget(self)

        self.bilibili_item = self.pivot.addItem(
            routeKey="bilibili",
            text=self.tr("Bilibili Summary"),
            onClick=lambda: self.stacked_widget.setCurrentWidget(self.bilibili_page),
        )
        self.other_item = self.pivot.addItem(
            routeKey="other",
            text=self.tr("Other Summary"),
            onClick=lambda: self.stacked_widget.setCurrentWidget(self.other_page),
        )

        self.stacked_widget.addWidget(self.bilibili_page)
        self.stacked_widget.addWidget(self.other_page)

        self.stacked_widget.setCurrentWidget(self.bilibili_page)
        self.pivot.setCurrentItem(self.bilibili_item)

        layout = QVBoxLayout(self)
        layout.addWidget(self.pivot)
        layout.addWidget(self.stacked_widget)


def _show_in_finder(file_path: str):
    """在 Finder 中显示文件"""
    if sys.platform == "darwin":
        subprocess.run(["open", "-R", file_path])
    elif sys.platform == "win32":
        subprocess.run(["explorer", "/select,", file_path])
    else:
        subprocess.run(["xdg-open", os.path.dirname(file_path)])
