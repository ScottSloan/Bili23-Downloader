from qfluentwidgets import SubtitleLabel, BodyLabel, TextEdit

from gui.component.dialog import DialogBase

from util.common.enum import ToastNotificationCategory

class BatchParseDialog(DialogBase):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.init_UI()

    def init_UI(self):
        caption_lab = SubtitleLabel(self.tr("Batch Parse"), parent = self)

        self.count_lab = BodyLabel(self.tr("Link Count: 0"), parent = self)

        self.lines_box = TextEdit(parent = self)
        self.lines_box.setPlaceholderText(self.tr("Paste video links here, one per line. Currently only av and BV links are supported."))

        self.viewLayout.addWidget(caption_lab)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(self.count_lab)
        self.viewLayout.addWidget(self.lines_box)

        self.widget.setMinimumWidth(550)

        self.yesButton.setText(self.tr("Start Parsing"))

        self.lines_box.textChanged.connect(self.on_lines_changed)

    def on_lines_changed(self):
        lines = self.lines_box.toPlainText().splitlines()
        count = len([line for line in lines if line.strip() != ""])

        self.count_lab.setText(self.tr("Link Count: {count}").format(count = count))

    def accept(self):
        # 检查链接是否属于 av 号或 BV 号链接，并去除空行
        lines = self.lines_box.toPlainText().splitlines()
        lines = [line.strip() for line in lines if line.strip() != ""]

        if not lines:
            self.show_top_toast_message(
                ToastNotificationCategory.ERROR,
                self.tr("No Links Provided"),
                self.tr("Please paste video links in the text box.")
            )
            return False

        for line in lines:
            if not "av" in line and not "BV" in line:
                self.show_top_toast_message(
                    ToastNotificationCategory.ERROR,
                    self.tr("Invalid Link Format"),
                    self.tr("Currently only av or BV links are supported.")
                )
                return False

        return super().accept()