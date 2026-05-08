from PySide6.QtCore import QObject, Signal, Slot

from util.parse.episode.tree import EpisodeData
from util.parse.episode.youtube import YouTubeEpisodeParser
from util.download.downloader.yt_dlp_downloader import get_node_exe, FFMPEG_DIR

from yt_dlp import YoutubeDL
from pathlib import Path
import os
import logging

logger = logging.getLogger(__name__)

class ParseWorker(QObject):
    success = Signal(str, dict)
    error = Signal(str)
    finished = Signal()

    def __init__(self, url: str, pn: int = 1, cookie_file: str = None):
        super().__init__()
        self.url = url
        self.pn = pn
        self.cookie_file = cookie_file

    @Slot()
    def run(self):
        EpisodeData.clear_cache()

        try:
            ydl_opts = {
                "quiet": True,
                "no_warnings": True,
                "skip_download": True,
            }
            
            # JavaScript 运行时配置
            node_exe = get_node_exe()
            if node_exe and os.path.exists(node_exe):
                ydl_opts["js_runtimes"] = {"node": {"path": node_exe}}
                logger.info(f"解析时使用 Node.js: {node_exe}")
            
            # FFmpeg 配置
            if FFMPEG_DIR and os.path.isdir(FFMPEG_DIR):
                ydl_opts["ffmpeg_location"] = FFMPEG_DIR
            
            # 针对 YouTube 的特殊处理
            if "youtube.com" in self.url or "youtu.be" in self.url:
                ydl_opts["extractor_args"] = {
                    "youtube": {
                        "player_client": ["android_vr", "tv"],
                        "player_skip": ["web", "mweb", "android", "ios"],
                    }
                }
                
                # 使用 cookies - 转换路径为 Windows 格式
                if self.cookie_file:
                    cookie_path = str(Path(self.cookie_file))
                    if os.path.exists(cookie_path):
                        ydl_opts["cookiefile"] = cookie_path
                        ydl_opts["forceipv4"] = True
                        ydl_opts["nocheckcertificate"] = True
                        logger.info(f"解析时使用 cookie 文件: {cookie_path}")
                    else:
                        logger.warning(f"Cookie 文件不存在: {cookie_path}")
                        # 尝试使用 Firefox cookies
                        ydl_opts["cookiesfrombrowser"] = ("firefox",)
                        logger.info("尝试使用 Firefox cookies")
                else:
                    # 未提供 cookie 文件，尝试使用 Firefox cookies
                    ydl_opts["cookiesfrombrowser"] = ("firefox",)
                    logger.info("尝试使用 Firefox cookies")

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
