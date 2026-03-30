from PySide6.QtGui import QIcon

from qfluentwidgets import FluentIcon

from gui.dialog.download_options import MediaSettingsPage, AdditionalSettingsPage, DownloadSettingsPage
from gui.component.dialog import TopNavigationDialogBase

from util.common import ExtendedFluentIcon

class DownloadOptionsDialog(TopNavigationDialogBase):
    def __init__(self, parent = None):
        super().__init__(parent)

        self.setWindowTitle(self.tr("Download Options"))
        self.setWindowIcon(QIcon(":/bili23/icon/app.svg"))

        self.setFixedSize(750, 500)

        self.init_UI()

    def init_UI(self):
        self.media_settings_page = MediaSettingsPage(self)
        self.additional_settings_page = AdditionalSettingsPage(self)
        self.download_settings_page = DownloadSettingsPage(self)

        self.addItem("media", self.tr("Media Settings"), FluentIcon.MEDIA, self.media_settings_page)
        self.addItem("additional", self.tr("Additional Files"), ExtendedFluentIcon.DOCUMENT, self.additional_settings_page)
        self.addItem("download", self.tr("Download Settings"), FluentIcon.DOWNLOAD, self.download_settings_page)

        self.pivot.setCurrentItem("media")
    
    def accept(self):
        # 检查用户的设置
        if not self.media_settings_page.on_check():
            return

        self.media_settings_page.on_save()
        self.download_settings_page.on_save()

        return super().accept()
