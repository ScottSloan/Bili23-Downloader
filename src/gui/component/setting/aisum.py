"""
Cloudflare Workers AI 设置卡片
"""

from PySide6.QtWidgets import QHBoxLayout, QFrame, QVBoxLayout, QWidget

from qfluentwidgets import (
    LineEdit, ComboBox, BodyLabel, PrimaryPushButton,
)

from util.common.data.aisum_models import (
    DEFAULT_MODELS, DEFAULT_MODEL_ID, SummaryUploadMethod,
)
from util.common.config import config


# ============= 行内编辑卡片基类 =============
class _InlineEditCard(QFrame):
    """当前值 + [Edit] 按钮 -> 点击后替换为 LineEdit + [Save] [Cancel]"""

    def __init__(self, title: str, parent=None):
        super().__init__(parent)

        self._title_label = BodyLabel(title, self)
        self._value_label = BodyLabel("", self)
        self._edit_btn = PrimaryPushButton(self.tr("Edit"), self)

        self._display_widget = QWidget(self)
        display_layout = QHBoxLayout(self._display_widget)
        display_layout.setContentsMargins(0, 0, 0, 0)
        display_layout.addStretch(1)
        display_layout.addWidget(self._value_label)
        display_layout.addSpacing(8)
        display_layout.addWidget(self._edit_btn)

        self._line_edit = LineEdit(self)
        self._line_edit.setClearButtonEnabled(True)
        self._save_btn = PrimaryPushButton(self.tr("Save"), self)
        self._cancel_btn = PrimaryPushButton(self.tr("Cancel"), self)

        self._edit_widget = QWidget(self)
        edit_layout = QHBoxLayout(self._edit_widget)
        edit_layout.setContentsMargins(0, 0, 0, 0)
        edit_layout.addWidget(self._line_edit, 1)
        edit_layout.addWidget(self._save_btn)
        edit_layout.addWidget(self._cancel_btn)
        self._edit_widget.setVisible(False)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(12, 8, 12, 8)
        main_layout.addWidget(self._title_label)
        main_layout.addWidget(self._display_widget)
        main_layout.addWidget(self._edit_widget)

        self._edit_btn.clicked.connect(self._enter_edit)
        self._cancel_btn.clicked.connect(self._exit_edit)
        self._save_btn.clicked.connect(self._on_save)

    def set_value_text(self, text: str):
        self._value_label.setText(text)

    def _enter_edit(self):
        self._line_edit.setText(self._value_label.text())
        self._display_widget.setVisible(False)
        self._edit_widget.setVisible(True)
        self._line_edit.setFocus()

    def _exit_edit(self):
        self._edit_widget.setVisible(False)
        self._display_widget.setVisible(True)

    def _on_save(self):
        value = self._line_edit.text().strip()
        self._on_save_value(value)
        self.set_value_text(value)
        self._exit_edit()

    def _on_save_value(self, value: str):
        pass


# ============= Cloudflare API Endpoint =============
class CloudflareEndpointSettingCard(_InlineEditCard):
    def __init__(self, parent=None):
        super().__init__(self.tr("Cloudflare API Endpoint"), parent)
        endpoint = config.get(config.cloudflare_endpoint)
        self.set_value_text(endpoint or self.tr("Not configured"))

    def _on_save_value(self, value: str):
        config.set(config.cloudflare_endpoint, value)


# ============= Cloudflare API Token =============
class CloudflareTokenSettingCard(_InlineEditCard):
    def __init__(self, parent=None):
        super().__init__(self.tr("Cloudflare API Token"), parent)
        self._mask_and_display()

    def _mask_and_display(self):
        token = config.get(config.cloudflare_token)
        if not token:
            self.set_value_text(self.tr("Not configured"))
        elif len(token) <= 12:
            self.set_value_text("****")
        else:
            self.set_value_text(token[:8] + "****" + token[-4:])

    def _on_save_value(self, value: str):
        config.set(config.cloudflare_token, value)
        self._mask_and_display()


# ============= AI 模型选择 =============
class CloudflareModelSettingCard(QFrame):
    def __init__(self, parent=None):
        super().__init__(parent)

        self.label = BodyLabel(self.tr("AI Model"), self)
        self.comboBox = ComboBox(self)
        for m in DEFAULT_MODELS:
            self.comboBox.addItem(m.display_name, userData=m.model_id)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.addWidget(self.label)
        layout.addStretch(1)
        layout.addWidget(self.comboBox)

        current = config.get(config.cloudflare_model) or DEFAULT_MODEL_ID
        for i in range(self.comboBox.count()):
            if self.comboBox.itemData(i) == current:
                self.comboBox.setCurrentIndex(i)
                break

        self.comboBox.currentIndexChanged.connect(self._on_model_changed)

    def _on_model_changed(self, index: int):
        if 0 <= index < len(DEFAULT_MODELS):
            config.set(config.cloudflare_model, DEFAULT_MODELS[index].model_id)


# ============= 上传方式选择 =============
class CloudflareUploadMethodSettingCard(QFrame):
    _method_texts = [
        "multipart/form-data",
        "Presigned URL (TBD)",
    ]
    _method_values = [
        SummaryUploadMethod.FORM_DATA,
        SummaryUploadMethod.PRESIGNED_URL,
    ]

    def __init__(self, parent=None):
        super().__init__(parent)

        self.label = BodyLabel(self.tr("Upload Method"), self)
        self.comboBox = ComboBox(self)
        self.comboBox.addItems(self._method_texts)

        layout = QHBoxLayout(self)
        layout.setContentsMargins(12, 8, 12, 8)
        layout.addWidget(self.label)
        layout.addStretch(1)
        layout.addWidget(self.comboBox)

        current = config.get(config.cloudflare_upload_method)
        for i, val in enumerate(self._method_values):
            if val == current:
                self.comboBox.setCurrentIndex(i)
                break

        self.comboBox.currentIndexChanged.connect(self._on_method_changed)

    def _on_method_changed(self, index: int):
        if 0 <= index < len(self._method_values):
            config.set(config.cloudflare_upload_method, self._method_values[index])
