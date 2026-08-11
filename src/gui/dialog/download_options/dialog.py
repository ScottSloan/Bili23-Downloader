from PySide6.QtCore import QSize
from PySide6.QtGui import QIcon

from qfluentwidgets import FluentIcon, MessageBox

from gui.component.dialog import TopNavigationDialogBase
from .additional import AdditionalSettingsPage
from .download import DownloadSettingsPage
from .media import MediaSettingsPage
from .preview import DownloadPreviewBar

from util.common.icon import ExtendedFluentIcon

class DownloadOptionsDialog(TopNavigationDialogBase):
    def __init__(self, parent = None):
        super().__init__(QSize(750, 500), parent)

        self.main_window = parent

        self.setWindowTitle(self.tr("Download Options"))
        self.setWindowIcon(QIcon(":/bili23/icon/app.svg"))

        self.setFixedSize(750, 500)

        self.init_UI()

        self.connect_signals()

        self.set_open_state(True)

    def init_UI(self):
        self.media_settings_page = MediaSettingsPage(self)
        self.additional_settings_page = AdditionalSettingsPage(self, self)
        self.download_settings_page = DownloadSettingsPage(self)

        self.addItem("media", self.tr("Media Settings"), FluentIcon.MEDIA, self.media_settings_page)
        self.addItem("additional", self.tr("Additional Files"), ExtendedFluentIcon.DOCUMENT, self.additional_settings_page)
        self.addItem("download", self.tr("Download Settings"), FluentIcon.DOWNLOAD, self.download_settings_page)

        self.pivot.setCurrentItem("media")

        self.preview_bar = DownloadPreviewBar(self)

        self.setBottomLeftWidget(self.preview_bar)

        self.on_update_preview()

    def connect_signals(self):
        self.media_settings_page.preview_changed.connect(self.on_update_preview)
        self.additional_settings_page.preview_changed.connect(self.on_update_preview)

    def on_update_preview(self):
        # 汇总各页面的下载内容，刷新底部的预览标签
        state = self.media_settings_page.get_download_preview()
        state.update(self.additional_settings_page.get_download_preview())

        self.preview_bar.update_preview(state)


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
    
    def closeEvent(self, event):
        super().closeEvent(event)

        self.set_open_state(False)

    def set_open_state(self, open: bool):
        self.main_window.parse_interface.download_options_dialog_opened = open
