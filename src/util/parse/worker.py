from PySide6.QtCore import QObject, Signal, Slot

from util.parse.episode.tree import EpisodeData
from util.parse.episode.youtube import YouTubeEpisodeParser
from util.parse.episode.bilibili import BilibiliEpisodeParser
from util.parse.youtube_api import extract_video_id, extract_playlist_id, get_video_info, get_playlist_items
from util.download.downloader.yt_dlp_downloader import get_node_exe, FFMPEG_DIR

from yt_dlp import YoutubeDL
from pathlib import Path
import os
import re
import logging
import time

logger = logging.getLogger(__name__)

class ParseWorker(QObject):
    success = Signal(str, dict)
    error = Signal(str)
    finished = Signal()

    _cache = {}
    _cache_ttl = 300

    def __init__(self, url: str, pn: int = 1, cookie_file: str = None):
        super().__init__()
        self.url = self._extract_url(url)
        self.pn = pn
        self.cookie_file = cookie_file

    def _extract_url(self, text: str) -> str:
        url_pattern = re.compile(r'https?://[^\s\'"<>]+')
        match = url_pattern.search(text)
        if match:
            return match.group(0)
        return text

    @classmethod
    def _get_cached(cls, key: str):
        if key in cls._cache:
            entry = cls._cache[key]
            if time.time() - entry["time"] < cls._cache_ttl:
                return entry["data"]
            del cls._cache[key]
        return None

    @classmethod
    def _set_cache(cls, key: str, data):
        cls._cache[key] = {"data": data, "time": time.time()}

    def _try_youtube_api(self) -> dict | None:
        """尝试使用YouTube API快速解析"""
        # 首先检查是否为播放列表
        playlist_id = extract_playlist_id(self.url)
        if playlist_id:
            entries = get_playlist_items(playlist_id, max_results=500)  # 获取最多500个视频
            if entries:
                # 获取播放列表的标题信息（使用第一个视频的信息作为参考）
                return {
                    "id": playlist_id,
                    "title": f"YouTube 播放列表 (ID: {playlist_id})",
                    "entries": entries,
                    "is_playlist": True,
                }
            return None
        
        # 处理单个视频
        video_id = extract_video_id(self.url)
        if video_id:
            return get_video_info(video_id)
        return None

    @Slot()
    def run(self):
        EpisodeData.clear_cache()

        try:
            info = None

            if "youtube.com" in self.url or "youtu.be" in self.url:
                cache_key = f"ytapi:{self.url}"
                cached = self._get_cached(cache_key)
                if cached:
                    info = cached
                else:
                    api_info = self._try_youtube_api()
                    if api_info:
                        info = api_info
                        self._set_cache(cache_key, info)
                        logger.info(f"YouTube API 快速解析成功: {info.get('title', '')[:30]}")

            if not info:
                ydl_opts = {
                    "quiet": True,
                    "no_warnings": True,
                    "skip_download": True,
                    "no_write_cookies": True,
                }
                
                # JavaScript 运行时配置
                node_exe = get_node_exe()
                if node_exe and os.path.exists(node_exe):
                    ydl_opts["js_runtimes"] = {"node": {"path": node_exe}}
                
                # FFmpeg 配置
                if FFMPEG_DIR and os.path.isdir(FFMPEG_DIR):
                    ydl_opts["ffmpeg_location"] = FFMPEG_DIR
                
                # 针对 YouTube 的特殊处理
                if "youtube.com" in self.url or "youtu.be" in self.url:
                    ydl_opts["extractor_args"] = {
                        "youtube": {
                            "player_client": ["web", "web_embedded"],
                            "player_skip": ["webpage"],
                        },
                        "youtubetab": {
                            "skip": ["authcheck"],
                        },
                    }
                    ydl_opts["extract_flat"] = "in_playlist"
                    
                    # 使用 cookies
                    if self.cookie_file:
                        cookie_path = str(Path(self.cookie_file))
                        if os.path.exists(cookie_path):
                            ydl_opts["cookiefile"] = cookie_path
                            ydl_opts["forceipv4"] = True
                            ydl_opts["nocheckcertificate"] = True
                        else:
                            ydl_opts["cookiesfrombrowser"] = ("firefox",)
                    else:
                        ydl_opts["cookiesfrombrowser"] = ("firefox",)

                cache_key = f"ytdl:{self.url}:{self.cookie_file}"
                cached = self._get_cached(cache_key)
                if cached:
                    info = cached
                else:
                    with YoutubeDL(ydl_opts) as ydl:
                        info = ydl.extract_info(self.url, download=False)
                    self._set_cache(cache_key, info)

            if not info:
                raise ValueError("无法获取视频信息")

            if "bilibili.com" in self.url:
                episode_parser = BilibiliEpisodeParser(info.copy(), "VIDEO")
            else:
                episode_parser = YouTubeEpisodeParser(info.copy(), "VIDEO")
            episode_parser.parse()

            self.success.emit("VIDEO", {})

        except Exception as e:
            self.error.emit(str(e))

        finally:
            self.finished.emit()
            self.deleteLater()
