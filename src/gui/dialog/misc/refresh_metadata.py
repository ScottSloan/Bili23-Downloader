from PySide6.QtWidgets import QFormLayout
from qfluentwidgets import BodyLabel, ComboBox, SubtitleLabel

from gui.component.dialog import DialogBase
from gui.component.widget.spinbox import SpinBox
from util.common.enum import MetadataType


class RefreshMetadataDialog(DialogBase):
    def __init__(self, count: int, parent):
        super().__init__(parent)
        self.viewLayout.addWidget(SubtitleLabel(self.tr("Refresh Metadata"), self))

        description = BodyLabel(self.tr(
            "Refresh metadata for {count} video(s). Existing files in the chosen format will be replaced."
        ).format(count = count), self)
        description.setWordWrap(True)
        self.viewLayout.addWidget(description)

        self.format_box = ComboBox(self)
        for format in (MetadataType.JSON, MetadataType.NFO):
            self.format_box.addItem(format.name, userData = format)

        self.batch_size_box = SpinBox(self)
        self.batch_size_box.setRange(1, min(50, count))
        self.batch_size_box.setValue(1)

        self.pause_box = SpinBox(self)
        self.pause_box.setRange(1, 120)
        self.pause_box.setValue(2)

        form = QFormLayout()
        form.addRow(self.tr("Format"), self.format_box)
        form.addRow(self.tr("Videos per batch"), self.batch_size_box)
        form.addRow(self.tr("Seconds between batches"), self.pause_box)
        self.viewLayout.addLayout(form)
        self.yesButton.setText(self.tr("Refresh"))
        self.widget.setMinimumWidth(420)

    def accept(self):
        self.options = (self.format_box.currentData(), self.batch_size_box.value(), self.pause_box.value())
        return super().accept()
