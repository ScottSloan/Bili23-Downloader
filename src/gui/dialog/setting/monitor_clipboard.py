from PySide6.QtWidgets import QHBoxLayout

from qfluentwidgets import SubtitleLabel, BodyLabel, HyperlinkLabel

from gui.component.dialog import DialogBase
from gui.component.widget import LabelSwitchButton

from util.common.config import config

class MonitorClipboardDialog(DialogBase):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.init_UI()

        self.init_data()

    def init_UI(self):
        caption_lab = SubtitleLabel(self.tr("Monitor Clipboard Settings"), self)

        self.monitor_clipboard_switch = LabelSwitchButton(self.tr("Monitor Clipboard"), parent = self)
        self.monitor_clipboard_switch.switch.onText = self.tr("On - Automatically start parsing when a link is copied")
        self.monitor_clipboard_switch.switch.offText = self.tr("Off - Do not monitor clipboard")

        self.show_download_confirmation_dialog_switch = LabelSwitchButton(self.tr("Automatically Show Download Confirmation Dialog"), parent = self)
        self.show_download_confirmation_dialog_switch.switch.onText = self.tr("On - Show the dialog after parsing a link")
        self.show_download_confirmation_dialog_switch.switch.offText = self.tr("Off - Do not show the dialog")
        self.show_download_confirmation_dialog_switch.showHyperLabel("注意事项")

        self.viewLayout.addWidget(caption_lab)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(self.monitor_clipboard_switch)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(self.show_download_confirmation_dialog_switch)

        self.widget.setMinimumWidth(450)

        self.monitor_clipboard_switch.switch.checkedChanged.connect(self.on_monitor_clipboard)

    def init_data(self):
        self.monitor_clipboard_switch.switch.setChecked(config.get(config.monitor_clipboard))
        self.show_download_confirmation_dialog_switch.switch.setChecked(config.get(config.show_download_confirmation_dialog))

        self.on_monitor_clipboard()

    def accept(self):
        config.set(config.monitor_clipboard, self.monitor_clipboard_switch.switch.isChecked())
        config.set(config.show_download_confirmation_dialog, self.show_download_confirmation_dialog_switch.switch.isChecked())

        return super().accept()
    
    def on_monitor_clipboard(self):
        enabled = self.monitor_clipboard_switch.switch.isChecked()

        self.show_download_confirmation_dialog_switch.setEnabled(enabled)

        if not enabled:
            self.show_download_confirmation_dialog_switch.switch.setChecked(False)
