from PySide6.QtCore import QObject, Signal, Slot

from util.parse.episode.tree import EpisodeData
from util.parse.episode.youtube import YouTubeEpisodeParser

from yt_dlp import YoutubeDL
import logging

logger = logging.getLogger(__name__)

class ParseWorker(QObject):
    success = Signal(str, dict)
    error = Signal(str)
    finished = Signal()

    def __init__(self, url: str, pn: int = 1):
        super().__init__()
        self.url = url
        self.pn = pn

    @Slot()
    def run(self):
        EpisodeData.clear_cache()

        try:
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
            }

            with YoutubeDL(ydl_opts) as ydl:
                info = ydl.extract_info(self.url, download=False)

            if not info:
                raise ValueError("无法获取视频信息")

            episode_parser = YouTubeEpisodeParser(info.copy(), "VIDEO")
            episode_parser.parse()

            self.success.emit("VIDEO", {})

        except Exception as e:
            self.error.emit(str(e))

        finally:
            self.finished.emit()
            self.deleteLater()
