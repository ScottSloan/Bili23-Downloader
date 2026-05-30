from qfluentwidgets import SwitchButton, SubtitleLabel

from gui.component.dialog import DialogBase
from gui.component.widget import LabelSwitchButton

class MonitorClipboardDialog(DialogBase):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.init_UI()

    def init_UI(self):
        caption_lab = SubtitleLabel(self.tr("Monitor Clipboard Settings"), self)

        self.monitor_clipboard_switch = LabelSwitchButton(self.tr("Monitor Clipboard"), parent = self)
        self.monitor_clipboard_switch.switch.onText = self.tr("On - Automatically start parsing when a link is copied")
        self.monitor_clipboard_switch.switch.offText = self.tr("Off - Do not monitor clipboard")

        self.show_download_options_dialog_switch = LabelSwitchButton(self.tr("Show Download Confirmation Dialog"), parent = self)
        self.show_download_options_dialog_switch.switch.onText = self.tr("On - Show the dialog after parsing a link")
        self.show_download_options_dialog_switch.switch.offText = self.tr("Off - Do not show the dialog")

        self.viewLayout.addWidget(caption_lab)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(self.monitor_clipboard_switch)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(self.show_download_options_dialog_switch)

        self.widget.setMinimumWidth(450)


