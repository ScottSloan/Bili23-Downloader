from PySide6.QtWidgets import QVBoxLayout
from PySide6.QtCore import QTimer

from gui.dialog.download_options.card import MediaInfoCard, MediaOptionsCard, MessageBox
from gui.component.widget import ScrollArea

from util.parse.preview import PreviewerInfo
from util.common import signal_bus, config

class MediaSettingsPage(ScrollArea):
    def __init__(self, parent = None):
        super().__init__(parent = parent)

        self.options_dialog = parent

        self.init_UI()

        self.init_media_info()

        QTimer.singleShot(0, self.media_info_card.toggleExpand)

    def init_UI(self):
        self.media_info_card = MediaInfoCard(self.options_dialog, parent = self)
        self.media_options_card = MediaOptionsCard(parent = self)
        
        main_layout = QVBoxLayout()
        main_layout.addWidget(self.media_info_card)
        main_layout.addWidget(self.media_options_card)
        main_layout.addStretch()

        self.setScrollLayout(main_layout)
    
    def connect_signals(self):
        self.media_info_card.video_quality_choice.currentIndexChanged.connect(self.on_change_video_info_choice)
        self.media_info_card.audio_quality_choice.currentIndexChanged.connect(self.on_change_audio_info_choice)
        self.media_info_card.video_codec_choice.currentIndexChanged.connect(self.on_change_video_info_choice)

    def init_media_info(self):
        self.media_info_card.update_choice_data(PreviewerInfo.video_quality_choice_data, PreviewerInfo.audio_quality_choice_data, PreviewerInfo.video_codec_choice_data)

        self.on_change_video_info_choice()
        self.on_change_audio_info_choice()

        self.connect_signals()

    def on_change_video_info_choice(self):
        self.media_info_card.pre_query_video_info()

        signal_bus.parse.query_video_info.emit(
            self.media_info_card.video_quality_id,
            self.media_info_card.video_codec_id,
            self.media_info_card.on_query_video_info
        )

    def on_change_audio_info_choice(self):
        self.media_info_card.pre_query_audio_info()

        signal_bus.parse.query_audio_info.emit(
            self.media_info_card.audio_quality_id,
            self.media_info_card.on_query_audio_info
        )

    def on_save(self):
        config.video_quality_id = self.media_info_card.video_quality_id
        config.audio_quality_id = self.media_info_card.audio_quality_id
        config.video_codec_id = self.media_info_card.video_codec_id

        config.download_video_stream = self.media_options_card.download_video_stream
        config.download_audio_stream = self.media_options_card.download_audio_stream
        config.merge_video_audio = self.media_options_card.merge_video_audio
        config.keep_original_files = self.media_options_card.keep_original_files

    def on_check(self):
        # 只下载独立视频流会导致没有声音，提示用户确认
        download_video = self.media_options_card.download_video_stream
        download_audio = self.media_options_card.download_audio_stream
        merge = self.media_options_card.merge_video_audio

        if not download_audio and download_video:
            dialog = MessageBox(
                self.tr("Important Notice"),
                self.tr("Downloading video only will result in a silent video.\n\nIf you intentionally need a video without audio, you may proceed. Otherwise, please also enable the audio stream."),
                self.options_dialog
            )

            return dialog.exec()
        
        # 未选择合并视频和音频会导致下载两个分开的文件，提示用户确认
        if not merge and download_video and download_audio:
            dialog = MessageBox(
                self.tr("Important Notice"),
                self.tr('"Merge video and audio" is disabled. Video and audio will be downloaded as two separate files.\n\nTo get a single complete video file, please enable "Merge video and audio".'),
                self.options_dialog
            )

            return dialog.exec()

            
        return True
    
    def has_media_to_download(self):
        return (
            self.media_options_card.download_video_stream or
            self.media_options_card.download_audio_stream
        )