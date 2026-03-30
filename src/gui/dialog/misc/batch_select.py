from qfluentwidgets import SubtitleLabel, LineEdit

from gui.component.dialog import DialogBase

from util.common.enum import ToastNotificationCategory

class BatchSelectDialog(DialogBase):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.init_UI()

        self.number_list = []

    def init_UI(self):
        self.caption_label = SubtitleLabel(self.tr("Batch Selection"), parent = self)

        self.lines_box = LineEdit(parent = self)
        self.lines_box.setPlaceholderText(self.tr("Enter line numbers (e.g. 1,3,5-10)"))
        self.lines_box.setClearButtonEnabled(True)

        self.viewLayout.addWidget(self.caption_label)
        self.viewLayout.addSpacing(10)
        self.viewLayout.addWidget(self.lines_box)

        self.widget.setMinimumWidth(450)

    def accept(self):
        self.number_list = self.to_number_list()

        return super().accept()
    
    @property
    def number_str(self):
        return self.lines_box.text().strip().split(",")
    
    def to_number_list(self):
        number_list = []

        for line in self.number_str:
            if "-" in line:
                start, end = line.split("-")
                number_list.extend(range(int(start), int(end) + 1))
            else:
                number_list.append(int(line))
        
        return number_list
    
    def validate(self):
        def setError(message = ""):
            self.lines_box.setFocus()
            self.lines_box.setError(True)

            self.show_top_toast_message(ToastNotificationCategory.ERROR, "", message)

        if self.lines_box.text().strip() == "":
            setError(self.tr("Please enter line numbers"))

            return False
        
        for line in self.number_str:
            if "-" in line:
                start, end = line.split("-")

                if not start.isdigit() or not end.isdigit() or int(start) <= 0 or int(end) <= 0 or int(start) > int(end):
                    setError(self.tr("Invalid line number range"))

                    return False
            else:
                if not line.isdigit() or int(line) <= 0:
                    setError(self.tr("Invalid line number"))

                    return False
        
        return True
