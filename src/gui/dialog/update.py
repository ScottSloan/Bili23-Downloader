from PySide6.QtWidgets import QVBoxLayout, QWidget, QHBoxLayout
from PySide6.QtGui import QIcon

from qfluentwidgets import BodyLabel, SubtitleLabel, PushButton, PrimaryPushButton, TextBrowser, CaptionLabel

from gui.component.dialog import FluentDialogBase
from gui.component.widget import SectionLabel

from util.common.style_sheet import StyleSheet

class UpdateDialog(FluentDialogBase):
    def __init__(self, parent = None):
        super().__init__(parent = None)

        self._parent_window = parent

        self.setWindowTitle(self.tr("软件更新"))
        self.setWindowIcon(QIcon(":/bili23/icon/app.svg"))

        self.setFixedSize(650, 450)

        self.init_UI()

    def init_UI(self):
        caption_lab = SubtitleLabel("新版本已经发布", parent = self)

        tip_lab = BodyLabel("2.00.0 版本可供下载，你当前使用的版本是 1.00.0。是否现在更新？", parent = self)

        log_lab = CaptionLabel("更新内容：")

        self.log_browser = TextBrowser(self)
        self.log_browser.setReadOnly(True)
        self.log_browser.setMarkdown(" # 2.00.0\n\n * 修复一些已知问题")

        self.skip_btn = PushButton(self.tr("跳过此版本"), parent = self)
        self.update_btn = PrimaryPushButton(self.tr("立即更新"), parent = self)

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
