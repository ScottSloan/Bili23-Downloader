from PySide6.QtGui import QIcon

from qfluentwidgets import FluentIcon, MessageBox

from gui.component.dialog import TopNavigationDialogBase
from .additional import AdditionalSettingsPage
from .download import DownloadSettingsPage
from .media import MediaSettingsPage

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
        
        if not self.media_settings_page.has_media_to_download() and not self.additional_settings_page.has_file_to_download():
            # 如果没有选择下载任何媒体文件，提示用户
            dialog = MessageBox(
                self.tr("No files selected for download"),
                self.tr("Please select at least one of the following: video stream, audio stream, or additional files."),
                self
            )
            dialog.hideCancelButton()
            dialog.exec()
            
            return

        self.media_settings_page.on_save()
        self.download_settings_page.on_save()

        return super().accept()
