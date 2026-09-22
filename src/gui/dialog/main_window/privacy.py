from qfluentwidgets import SubtitleLabel, TextBrowser, setCustomStyleSheet

from gui.component.dialog import DialogBase

from util.common.translator import Translator

class PrivacyPolicyDialog(DialogBase):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.init_UI()

    def init_UI(self):
        caption_lab = SubtitleLabel(self.tr("Privacy Policy"), self)

        self.text_browser = TextBrowser(self)
        self.text_browser.setReadOnly(True)
        self.text_browser.setText(Translator.PRIVACY_POLICY())

        self.viewLayout.addWidget(caption_lab)
        self.viewLayout.addWidget(self.text_browser)

        self.widget.setMinimumSize(600, 450)

        self.__set_QSS()

        self.hideCancelButton()

    def __set_QSS(self):
        style = """TextBrowser {
            border: none;
            background-color: transparent;
        }

        TextBrowser:hover {
            background-color: transparent;
        }

        TextBrowser:focus {
            background-color: transparent;
        }"""

        setCustomStyleSheet(self.text_browser, style, style)
