from PySide6.QtWidgets import QVBoxLayout, QWidget, QHBoxLayout, QApplication
from PySide6.QtGui import QIcon

from qfluentwidgets import BodyLabel, SubtitleLabel, PushButton, PrimaryPushButton, TextBrowser, CaptionLabel

from gui.component.dialog import FluentDialogBase

from util.common.style_sheet import StyleSheet
from util.common.config import config

import webbrowser

class UpdateDialog(FluentDialogBase):
    def __init__(self, info: dict, parent = None):
        super().__init__(parent = None)

        self._parent_window = parent
        self._info = info
        self._can_close = not info["required"]

        self.setWindowTitle(self.tr("Update Available"))
        self.setWindowIcon(QIcon(":/bili23/icon/app.svg"))

        self.setFixedSize(650, 450)

        self.init_UI()

    def init_UI(self):
        caption_lab = SubtitleLabel(self.tr("A new version is available"), parent = self)

        tip_lab = BodyLabel(
            self.tr("Version {latest_version} is available for download. You are currently using version {current_version}. Would you like to update now?").format(
                latest_version = self._info["version"],
                current_version = config.app_version
            ),
            parent = self
        )
        tip_lab.setWordWrap(True)

        log_lab = CaptionLabel(self.tr("What's new:"))

        self.log_browser = TextBrowser(self)
        self.log_browser.setReadOnly(True)
        self.log_browser.setMarkdown(self._info["content"])

        self.skip_btn = PushButton(self.tr("Skip this version"), parent = self)
        self.update_btn = PrimaryPushButton(self.tr("Update now"), parent = self)

        content_widget = QWidget(self)
        content_widget.setContentsMargins(10, 10, 10, 5)

        button_layout = QHBoxLayout()
        button_layout.setContentsMargins(0, 0, 0, 0)
        button_layout.setSpacing(10)
        button_layout.addWidget(self.skip_btn)
        button_layout.addStretch()
        button_layout.addWidget(self.update_btn)

        vbox_layout = QVBoxLayout(content_widget)
        vbox_layout.setContentsMargins(0, 0, 0, 0)
        vbox_layout.setSpacing(10)
        vbox_layout.addWidget(caption_lab)
        vbox_layout.addWidget(tip_lab)
        vbox_layout.addSpacing(10)
        vbox_layout.addWidget(log_lab)
        vbox_layout.addWidget(self.log_browser)
        vbox_layout.addLayout(button_layout)

        self.vboxLayout = QVBoxLayout(self)
        self.vboxLayout.setContentsMargins(10, 32, 10, 10)
        self.vboxLayout.setSpacing(10)
        self.vboxLayout.addWidget(content_widget)

        StyleSheet.FLUENT_DIALOG.apply(self)

        self.set_required(self._info["required"])

        self.skip_btn.clicked.connect(self.on_skip)
        self.update_btn.clicked.connect(self.on_update)

    def closeEvent(self, e):
        if not self._can_close:
            e.ignore()
            return
        
        return super().closeEvent(e)

    def on_skip(self):
        config.set(config.skip_version, self._info["version"])

        self.close()

    def on_update(self):
        webbrowser.open(self._info["update_url"])

        if self._info["required"]:
            self._can_close = True
            self.close()
            QApplication.quit()

    def set_required(self, required: bool):
        if required:
            self.titleBar.closeBtn.hide()
            self.skip_btn.hide()
