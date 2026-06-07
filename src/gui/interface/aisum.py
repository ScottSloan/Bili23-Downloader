"""
AI 总结主界面模块

包含两个可切换子页面：
  - 子页面 1：B 站总结页（URL 输入 → 下载 → Cloudflare 三阶段总结）
  - 子页面 2：其他总结页（本地文件选择 → Cloudflare 总结）
"""

from PySide6.QtWidgets import (
    QFrame, QHBoxLayout, QVBoxLayout, QFileDialog, QTextEdit, QWidget,
    QDialog, QLineEdit as QLineEdit2, QLabel, QPushButton, QMessageBox,
)
from PySide6.QtCore import Qt
import uuid

from qfluentwidgets import (
    Pivot, PopUpAniStackedWidget, LineEdit, ComboBox, PrimaryPushButton,
    BodyLabel,
)

from gui.component.widget.button import IndeterminateProgressPushButton

from util.common.data.aisum_models import (
    SummaryType,
    PromptPreset, BUILTIN_PRESETS, DEFAULT_SLOT_MAPPING,
    serialize_presets, deserialize_presets,
    ProviderType, AISumModelConfig,
    load_aisum_models, save_aisum_models,
    WHISPER_MODEL_ID, WHISPER_MODEL_NAME,
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
# 模型编辑对话框
# ============================================================
class _ModelEditDialog(QDialog):
    """新增 / 编辑 AI 模型"""

    PROVIDER_LABELS = {
        ProviderType.CLOUDFLARE: "Cloudflare Workers AI",
        ProviderType.OPENAI: "OpenAI",
        ProviderType.OLLAMA: "Ollama",
        ProviderType.CUSTOM: "Custom",
    }

    def __init__(self, model: AISumModelConfig = None, parent=None):
        super().__init__(parent)
        self._model = model
        self.setWindowTitle(self.tr("New Model") if model is None else self.tr("Edit Model"))
        self.resize(500, 350)
        self._result = None

        layout = QVBoxLayout(self)

        # Title
        title_label = QLabel(self.tr("Title:"), self)
        self._title_edit = QLineEdit2(self)
        self._title_edit.setPlaceholderText(self.tr("e.g. Llama 3.2 3B"))

        # Model ID
        model_id_label = QLabel(self.tr("Model ID:"), self)
        self._model_id_edit = QLineEdit2(self)
        self._model_id_edit.setPlaceholderText(self.tr("e.g. @cf/meta/llama-3.2-3b-instruct"))

        # Provider
        provider_label = QLabel(self.tr("Provider:"), self)
        self._provider_combo = ComboBox(self)
        for pt in ProviderType:
            self._provider_combo.addItem(self.PROVIDER_LABELS.get(pt, pt.value), userData=pt)
        self._provider_combo.currentIndexChanged.connect(self._on_provider_changed)

        # Custom endpoint (only visible for non-Cloudflare)
        endpoint_label = QLabel(self.tr("API Endpoint:"), self)
        self._endpoint_edit = QLineEdit2(self)
        self._endpoint_edit.setPlaceholderText(self.tr("e.g. http://localhost:11434/v1"))

        # API Key
        api_key_label = QLabel(self.tr("API Key (optional):"), self)
        self._api_key_edit = QLineEdit2(self)
        self._api_key_edit.setPlaceholderText(self.tr("sk-..."))

        # Buttons
        btn_layout = QHBoxLayout()
        self._save_btn = QPushButton(self.tr("Save"), self)
        self._cancel_btn = QPushButton(self.tr("Cancel"), self)
        btn_layout.addStretch()
        btn_layout.addWidget(self._cancel_btn)
        btn_layout.addWidget(self._save_btn)

        layout.addWidget(title_label)
        layout.addWidget(self._title_edit)
        layout.addWidget(model_id_label)
        layout.addWidget(self._model_id_edit)
        layout.addWidget(provider_label)
        layout.addWidget(self._provider_combo)
        layout.addWidget(endpoint_label)
        layout.addWidget(self._endpoint_edit)
        layout.addWidget(api_key_label)
        layout.addWidget(self._api_key_edit)
        layout.addStretch()
        layout.addLayout(btn_layout)

        # Pre-fill if editing
        if model:
            self._title_edit.setText(model.title)
            self._model_id_edit.setText(model.model_id)
            for i in range(self._provider_combo.count()):
                if self._provider_combo.itemData(i) == model.provider:
                    self._provider_combo.setCurrentIndex(i)
                    break
            self._endpoint_edit.setText(model.endpoint)
            self._api_key_edit.setText(model.api_key)

        self._save_btn.clicked.connect(self._on_save)
        self._cancel_btn.clicked.connect(self.reject)
        self._on_provider_changed()

    def _on_provider_changed(self):
        provider = self._provider_combo.itemData(self._provider_combo.currentIndex())
        is_cf = provider == ProviderType.CLOUDFLARE
        self._endpoint_edit.setEnabled(not is_cf)
        self._api_key_edit.setEnabled(not is_cf)

    def _on_save(self):
        title = self._title_edit.text().strip()
        model_id = self._model_id_edit.text().strip()
        if not title:
            QMessageBox.warning(self, self.tr("Error"), self.tr("Title cannot be empty."))
            return
        if not model_id:
            QMessageBox.warning(self, self.tr("Error"), self.tr("Model ID cannot be empty."))
            return
        provider = self._provider_combo.itemData(self._provider_combo.currentIndex())
        self._result = AISumModelConfig(
            id=self._model.id if self._model else str(uuid.uuid4()),
            title=title,
            model_id=model_id,
            provider=provider,
            endpoint=self._endpoint_edit.text().strip() if provider != ProviderType.CLOUDFLARE else "",
            api_key=self._api_key_edit.text().strip() if provider != ProviderType.CLOUDFLARE else "",
        )
        self.accept()

    def result(self) -> AISumModelConfig | None:
        return self._result


# ============================================================
# 提示词编辑对话框
# ============================================================
class _PromptEditDialog(QDialog):
    """新增 / 编辑提示词预设"""

    def __init__(self, preset: PromptPreset = None, parent=None):
        super().__init__(parent)
        self._preset = preset
        self.setWindowTitle(self.tr("New Preset") if preset is None else self.tr("Edit Preset"))
        self.resize(500, 400)
        self._result = None

        layout = QVBoxLayout(self)

        title_label = QLabel(self.tr("Title:"), self)
        self._title_edit = QLineEdit2(self)
        self._title_edit.setPlaceholderText(self.tr("e.g. Short Summary"))

        prompt_label = QLabel(self.tr("Prompt:"), self)
        self._prompt_edit = QTextEdit(self)
        self._prompt_edit.setPlaceholderText(self.tr("Enter the AI system prompt…"))

        btn_layout = QHBoxLayout()
        self._save_btn = QPushButton(self.tr("Save"), self)
        self._cancel_btn = QPushButton(self.tr("Cancel"), self)
        btn_layout.addStretch()
        btn_layout.addWidget(self._cancel_btn)
        btn_layout.addWidget(self._save_btn)

        layout.addWidget(title_label)
        layout.addWidget(self._title_edit)
        layout.addWidget(prompt_label)
        layout.addWidget(self._prompt_edit, 1)
        layout.addLayout(btn_layout)

        if preset:
            self._title_edit.setText(preset.title)
            self._prompt_edit.setPlainText(preset.prompt)

        self._save_btn.clicked.connect(self._on_save)
        self._cancel_btn.clicked.connect(self.reject)

    def _on_save(self):
        title = self._title_edit.text().strip()
        prompt = self._prompt_edit.toPlainText().strip()
        if not title:
            QMessageBox.warning(self, self.tr("Error"), self.tr("Title cannot be empty."))
            return
        if not prompt:
            QMessageBox.warning(self, self.tr("Error"), self.tr("Prompt cannot be empty."))
            return
        self._result = PromptPreset(
            id=self._preset.id if self._preset else str(uuid.uuid4()),
            title=title,
            prompt=prompt,
            builtin=False,
        )
        self.accept()

    def result(self) -> PromptPreset | None:
        return self._result


# ============================================================
# 子页面 1：B 站总结页
# ============================================================
class _BilibiliSumPage(QWidget):
    """B 站视频内容总结"""

    SLOT_LABELS = {
        "original": "Original",
        "refined": "Refined",
        "keypoints": "Keypoints",
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self._worker = None
        self._presets = list(BUILTIN_PRESETS)
        self._models = load_aisum_models()
        self.init_UI()
        self._load_presets()
        self._refresh_model_combo()

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

        # Transcription model dropdown (only visible for Audio)
        self._transcribe_label = BodyLabel(self.tr("Transcription:"), self)
        self._transcribe_combo = ComboBox(self)
        self._transcribe_combo.addItem(WHISPER_MODEL_NAME, userData=WHISPER_MODEL_ID)
        self._transcribe_label.setVisible(False)
        self._transcribe_combo.setVisible(False)

        self.submit_btn = IndeterminateProgressPushButton(self.tr("Summarize"), self)

        # —— 提示词预设管理区 ——
        preset_section_label = BodyLabel(self.tr("Prompt Configuration"), self)

        self._preset_widget = QWidget(self)
        preset_layout = QVBoxLayout(self._preset_widget)
        preset_layout.setContentsMargins(0, 0, 0, 0)

        self._slot_combos = {}   # slot_name → ComboBox
        self._edit_buttons = {}  # slot_name → QPushButton

        for slot_key in ("original", "refined", "keypoints"):
            row = QWidget(self._preset_widget)
            row_layout = QHBoxLayout(row)
            row_layout.setContentsMargins(0, 0, 0, 0)

            slot_label = BodyLabel(self.tr(self.SLOT_LABELS[slot_key]) + ":", row)
            slot_label.setFixedWidth(80)
            combo = ComboBox(row)
            self._slot_combos[slot_key] = combo
            combo.currentIndexChanged.connect(lambda idx, sk=slot_key: self._on_slot_changed(sk))

            edit_btn = PrimaryPushButton(self.tr("Edit"), row)
            self._edit_buttons[slot_key] = edit_btn
            edit_btn.clicked.connect(lambda checked=False, sk=slot_key: self._on_edit_preset(sk))

            row_layout.addWidget(slot_label)
            row_layout.addWidget(combo, 1)
            row_layout.addWidget(edit_btn)
            preset_layout.addWidget(row)

        new_btn = PrimaryPushButton(self.tr("New Preset"), self._preset_widget)
        new_btn.clicked.connect(self._on_new_preset)
        preset_layout.addWidget(new_btn, 0, Qt.AlignmentFlag.AlignLeft)

        # —— 模型管理区 ——
        model_section_label = BodyLabel(self.tr("Model Configuration"), self)

        self._model_widget = QWidget(self)
        model_mgmt_layout = QVBoxLayout(self._model_widget)
        model_mgmt_layout.setContentsMargins(0, 0, 0, 0)

        self._model_mgmt_combo = ComboBox(self._model_widget)
        self._model_edit_btn = PrimaryPushButton(self.tr("Edit"), self._model_widget)
        self._model_del_btn = PrimaryPushButton(self.tr("Delete"), self._model_widget)
        self._model_new_btn = PrimaryPushButton(self.tr("New Model"), self._model_widget)

        model_row = QWidget(self._model_widget)
        model_row_layout = QHBoxLayout(model_row)
        model_row_layout.setContentsMargins(0, 0, 0, 0)
        model_row_layout.addWidget(self._model_mgmt_combo, 1)
        model_row_layout.addWidget(self._model_edit_btn)
        model_row_layout.addWidget(self._model_del_btn)
        model_mgmt_layout.addWidget(model_row)
        model_mgmt_layout.addWidget(self._model_new_btn, 0, Qt.AlignmentFlag.AlignLeft)

        self._model_mgmt_combo.currentIndexChanged.connect(self._on_model_mgmt_selected)
        self._model_edit_btn.clicked.connect(self._on_edit_model)
        self._model_del_btn.clicked.connect(self._on_delete_model)
        self._model_new_btn.clicked.connect(self._on_new_model)

        # —— 结果区 ——
        result_label = BodyLabel(self.tr("Results:"), self)
        # ScrollArea 包裹结果区，避免内容多时拥挤
        from qfluentwidgets import ScrollArea
        self._result_scroll = ScrollArea(self)
        self._result_scroll.setWidgetResizable(True)
        self._result_scroll.setFixedHeight(180)
        self.result_widget = QWidget()
        self.result_layout = QVBoxLayout(self.result_widget)
        self.result_layout.setContentsMargins(0, 0, 0, 0)
        self.result_layout.setAlignment(Qt.AlignmentFlag.AlignTop)
        self._result_scroll.setWidget(self.result_widget)
        self._result_rows = []  # (QWidget, file_path)

        # —— 主布局 ——
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

        # Transcription row (visible only for Audio)
        transcribe_layout = QHBoxLayout()
        transcribe_layout.addWidget(self._transcribe_label)
        transcribe_layout.addWidget(self._transcribe_combo, 1)
        transcribe_layout.addStretch()
        main_layout.addLayout(transcribe_layout)

        main_layout.addSpacing(10)
        main_layout.addWidget(self.submit_btn, 0, Qt.AlignmentFlag.AlignLeft)

        main_layout.addSpacing(15)
        main_layout.addWidget(preset_section_label)
        main_layout.addWidget(self._preset_widget)

        main_layout.addSpacing(15)
        main_layout.addWidget(model_section_label)
        main_layout.addWidget(self._model_widget)

        main_layout.addSpacing(15)
        main_layout.addWidget(result_label)
        main_layout.addWidget(self._result_scroll, 1)

        self.submit_btn.clicked.connect(self._on_submit)
        self.type_combo.currentIndexChanged.connect(self._on_type_changed)

    # ==================== 预设管理 ====================
    def _load_presets(self):
        """从配置加载预设列表并刷新 UI"""
        presets_json = config.get(config.cloudflare_presets)
        self._presets = deserialize_presets(presets_json)
        self._refresh_combos()

    def _refresh_combos(self):
        """刷新所有 ComboBox"""
        for slot_key, combo in self._slot_combos.items():
            combo.blockSignals(True)
            combo.clear()
            for p in self._presets:
                combo.addItem(p.title, userData=p.id)
            combo.blockSignals(False)

            # 选中当前 slot 对应的预设
            config_attr = {
                "original": config.cloudflare_slot_original,
                "refined": config.cloudflare_slot_refined,
                "keypoints": config.cloudflare_slot_keypoints,
            }[slot_key]
            active_id = config.get(config_attr) or DEFAULT_SLOT_MAPPING[slot_key]
            for i in range(combo.count()):
                if combo.itemData(i) == active_id:
                    combo.setCurrentIndex(i)
                    break

        # 更新 Edit 按钮状态
        self._update_edit_button_states()

    def _refresh_model_combo(self):
        """Refresh both model_combo and _model_mgmt_combo from self._models"""
        self.model_combo.blockSignals(True)
        self.model_combo.clear()
        self._model_mgmt_combo.blockSignals(True)
        self._model_mgmt_combo.clear()

        for m in self._models:
            self.model_combo.addItem(m.title, userData=m.id)
            self._model_mgmt_combo.addItem(m.title, userData=m.id)

        self.model_combo.blockSignals(False)
        self._model_mgmt_combo.blockSignals(False)

        # Select current model from config
        current_id = config.get(config.cloudflare_model)
        if current_id:
            for i in range(self.model_combo.count()):
                if self.model_combo.itemData(i) == current_id:
                    self.model_combo.setCurrentIndex(i)
                    break

        self._on_model_mgmt_selected()

    # ==================== 模型管理 ====================
    def _on_model_mgmt_selected(self):
        idx = self._model_mgmt_combo.currentIndex()
        has = 0 <= idx < len(self._models)
        self._model_edit_btn.setEnabled(has)
        self._model_del_btn.setEnabled(has)

    def _on_new_model(self):
        dlg = _ModelEditDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            model = dlg.result()
            if model:
                self._models.append(model)
                save_aisum_models(self._models)
                self._refresh_model_combo()

    def _on_edit_model(self):
        idx = self._model_mgmt_combo.currentIndex()
        if idx < 0 or idx >= len(self._models):
            return
        dlg = _ModelEditDialog(model=self._models[idx], parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            updated = dlg.result()
            if updated:
                self._models[idx] = updated
                save_aisum_models(self._models)
                self._refresh_model_combo()

    def _on_delete_model(self):
        idx = self._model_mgmt_combo.currentIndex()
        if idx < 0 or idx >= len(self._models):
            return
        reply = QMessageBox.question(
            self, self.tr("Delete Model"),
            self.tr("Are you sure you want to delete this model?"),
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No,
        )
        if reply == QMessageBox.StandardButton.Yes:
            del self._models[idx]
            save_aisum_models(self._models)
            self._refresh_model_combo()

    def _get_selected_preset(self, slot_key: str) -> PromptPreset | None:
        """获取当前 slot 选中的预设"""
        combo = self._slot_combos[slot_key]
        preset_id = combo.itemData(combo.currentIndex())
        for p in self._presets:
            if p.id == preset_id:
                return p
        return None

    def _on_slot_changed(self, slot_key: str):
        """用户切换 ComboBox 选择"""
        preset = self._get_selected_preset(slot_key)
        if not preset:
            return
        config_attr = {
            "original": config.cloudflare_slot_original,
            "refined": config.cloudflare_slot_refined,
            "keypoints": config.cloudflare_slot_keypoints,
        }[slot_key]
        config.set(config_attr, preset.id)
        self._update_edit_button_states()

    def _update_edit_button_states(self):
        """更新 Edit 按钮状态"""
        for btn in self._edit_buttons.values():
            btn.setEnabled(True)
            btn.setToolTip("")

    def _on_new_preset(self):
        dlg = _PromptEditDialog(parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            preset = dlg.result()
            if preset:
                self._presets.append(preset)
                self._save_and_refresh()

    def _on_edit_preset(self, slot_key: str):
        preset = self._get_selected_preset(slot_key)
        if not preset:
            return
        dlg = _PromptEditDialog(preset=preset, parent=self)
        if dlg.exec() == QDialog.DialogCode.Accepted:
            updated = dlg.result()
            if updated:
                for i, p in enumerate(self._presets):
                    if p.id == updated.id:
                        self._presets[i] = updated
                        break
                self._save_and_refresh()

    def _save_and_refresh(self):
        """保存预设列表到配置并刷新 UI"""
        config.set(config.cloudflare_presets, serialize_presets(self._presets))
        self._refresh_combos()

    # ==================== 提交与结果 ====================
    def _on_type_changed(self):
        """Show/hide transcription combo based on summary type"""
        is_audio = SummaryType(self.type_combo.currentText()) == SummaryType.AUDIO
        self._transcribe_label.setVisible(is_audio)
        self._transcribe_combo.setVisible(is_audio)

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
        if 0 <= model_idx < len(self._models):
            config.set(config.cloudflare_model, self._models[model_idx].model_id)

        self.submit_btn.setIndeterminateState(True)
        self._clear_results()

        self._worker = SummaryWorker(url, summary_type)
        self._worker.success.connect(self._on_success)
        self._worker.error.connect(self._on_error)
        self._worker.finished.connect(self._on_finished)

        AsyncTask.run(self._worker)

    def _on_success(self, _json_path: str, original_path: str, refined_path: str, keypoints_path: str):
        # JSON 文件不在结果区显示（内部存储用）
        if original_path:
            self._add_result_row(self.tr("Original Text"), original_path)
        if refined_path:
            self._add_result_row(self.tr("Refined Summary"), refined_path)
        if keypoints_path:
            self._add_result_row(self.tr("Keypoints"), keypoints_path)

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

        self.result_layout.removeWidget(row)
        row.deleteLater()
        self._result_rows = [(r, f) for r, f in self._result_rows if f != file_path]

        signal_bus.toast.show.emit(
            ToastNotificationCategory.SUCCESS,
            self.tr("Deleted"),
            self.tr("File has been deleted.")
        )

    def _clear_results(self):
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

    def _on_success(self, original: str, refined: str, keypoints: str, combined: str):
        self.result_text.setPlainText(combined or original or refined or keypoints)
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
    if sys.platform == "darwin":
        subprocess.run(["open", "-R", file_path])
    elif sys.platform == "win32":
        subprocess.run(["explorer", "/select,", file_path])
    else:
        subprocess.run(["xdg-open", os.path.dirname(file_path)])
