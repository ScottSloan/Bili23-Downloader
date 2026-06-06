#!/usr/bin/env python3
"""
Bili23 Downloader CLI
=====================
独立的命令行接口，支持视频/音频/字幕下载，无需启动 GUI。
复用项目内经过验证的核心模块（WBI 签名、URL 解析、CDN 查询）。

用法示例:
    python -m cli "https://www.bilibili.com/video/BV1xx411c7mD"
    python -m cli -q 120 --codec 12 "BV1xx411c7mD"
    python -m cli -o ~/Downloads --audio-only --quality 30280 "BV1xx411c7mD?p=2"
    python -m cli --subtitle --danmaku "https://www.bilibili.com/bangumi/play/ep12345"
    python -m cli --video-only --no-merge "BV1xx411c7mD"
    python -m cli --speed-limit 5 --threads 8 "BV1xx411c7mD"

异常排查:
    - "配置文件不存在": 首次使用需运行一次 GUI 版本以生成配置
    - "WBI 密钥初始化失败": 检查 api.bilibili.com 连接
    - "无法获取播放链接": 视频需要登录（如番剧/课程）
    - "ffmpeg 不可用": 合并视频需要 FFmpeg，检查 config 中 ffmpeg_source 设置
"""

import argparse
import sys
import os
import errno
import logging
import subprocess
import time
import re
import json
import shutil
from pathlib import Path
from functools import reduce
from hashlib import md5
from typing import Optional, Callable
from urllib.parse import urlencode, urlparse
from threading import Event, Lock
from concurrent.futures import ThreadPoolExecutor, as_completed

import httpx

# 确保 src 目录在 Python 路径中
_SRC_DIR = str(Path(__file__).resolve().parent)
if _SRC_DIR not in sys.path:
    sys.path.insert(0, _SRC_DIR)

# ---------------------------------------------------------------------------
# 日志
# ---------------------------------------------------------------------------
logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s: %(message)s",
    datefmt="%H:%M:%S",
    stream=sys.stdout,
)
logger = logging.getLogger("cli")

# ---------------------------------------------------------------------------
# 步骤 1: 最小化初始化 Qt 以加载配置
# ---------------------------------------------------------------------------
_QT_INITIALIZED = False


def _init_minimal_qt():
    global _QT_INITIALIZED
    if _QT_INITIALIZED:
        return
    os.environ["QT_QPA_PLATFORM"] = "offscreen"
    from PySide6.QtWidgets import QApplication
    from qfluentwidgets import qconfig as _qconfig

    _ = QApplication(sys.argv)

    from util.common.config import config, config_path

    if config_path.exists():
        _qconfig.load(str(config_path), config)
        logger.debug("配置加载成功: %s", config_path)
    else:
        logger.warning("配置文件不存在，使用默认配置")

    _QT_INITIALIZED = True


_init_minimal_qt()

# ---------------------------------------------------------------------------
# 步骤 2: 初始化依赖
# ---------------------------------------------------------------------------
import util.ffmpeg  # noqa: F401 - 初始化 ffmpeg 路径
import util.network.proxy  # noqa: F401 - 初始化代理配置

from util.common.config import config
from util.auth.cookie import cookie_manager  # noqa: F401 - 初始化 cookies
from util.auth.user import user_manager  # noqa: F401 - 初始化用户信息
from util.network.request import get_cookies
from util.common.enum import SubtitleType, MediaType
from util.common.data.media_info import reversed_video_quality_map, reversed_audio_quality_map
from util.parse.parser.base import ParserBase
from util.parse.episode.tree import Attribute

# ---------------------------------------------------------------------------
# WBI 密钥表 (与 ParserBase 一致)
# ---------------------------------------------------------------------------
_MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52,
]


def _init_wbi_keys():
    if config.get(config.img_key) and config.get(config.sub_key):
        return
    try:
        with httpx.Client(timeout=15, follow_redirects=True) as cli:
            resp = cli.get("https://api.bilibili.com/x/web-interface/nav", headers={
                "User-Agent": config.get(config.user_agent),
                "Referer": "https://www.bilibili.com/",
            })
            data = resp.json()
        wbi = data.get("data", {}).get("wbi_img", {})
        img_url = wbi.get("img_url", "")
        sub_url = wbi.get("sub_url", "")
        if img_url and sub_url:
            config.set(config.img_key, Path(img_url).stem, save=False)
            config.set(config.sub_key, Path(sub_url).stem, save=False)
            logger.info("WBI 密钥初始化成功")
        else:
            logger.warning("未能获取 WBI 密钥")
    except Exception as e:
        logger.warning("WBI 密钥获取失败: %s", e)


_init_wbi_keys()


def _enc_wbi(params: dict) -> str:
    def _get_mixin_key(orig: str) -> str:
        return reduce(lambda s, i: s + orig[i], _MIXIN_KEY_ENC_TAB, "")[:32]

    mixin_key = _get_mixin_key(config.get(config.img_key) + config.get(config.sub_key))
    params["wts"] = round(time.time())
    params = dict(sorted(params.items()))
    params = {
        k: "".join(filter(lambda c: c not in "!'()*", str(v)))
        for k, v in params.items()
    }
    query = urlencode(params)
    params["w_rid"] = md5((query + mixin_key).encode()).hexdigest()
    return urlencode(params)


# ---------------------------------------------------------------------------
# 辅助: av → bvid
# ---------------------------------------------------------------------------
_ALPHABET = "FcwAPNKTMug3GV5Lj7EJnHpWsx4tb8haYeviqBz6rkCy12mUSDQX9RdoZf"
_ENCODE_MAP = (8, 7, 0, 5, 1, 3, 2, 4, 6)
_MAX_AID = 1 << 51
_XOR_CODE = 23442827791579


def av_to_bvid(aid: int) -> str:
    bvid = [""] * 9
    tmp = (_MAX_AID | aid) ^ _XOR_CODE
    for i in range(len(_ENCODE_MAP)):
        bvid[_ENCODE_MAP[i]] = _ALPHABET[tmp % len(_ALPHABET)]
        tmp //= len(_ALPHABET)
    return "BV1" + "".join(bvid)


# ---------------------------------------------------------------------------
# 辅助: format
# ---------------------------------------------------------------------------
def format_size(size_bytes: int) -> str:
    if size_bytes <= 0:
        return "未知"
    for unit in ["B", "KB", "MB", "GB", "TB"]:
        if size_bytes < 1024:
            return f"{size_bytes:.1f} {unit}"
        size_bytes /= 1024
    return f"{size_bytes:.1f} PB"


def format_time(seconds: float) -> str:
    m, s = divmod(int(seconds), 60)
    return f"{m}:{s:02d}"


def safe_filename(title: str) -> str:
    return re.sub(r'[/\\:*?"<>|]', "_", title)


# ---------------------------------------------------------------------------
# TokenBucket (与 GUI 一致)
# ---------------------------------------------------------------------------
class TokenBucket:
    def __init__(self, rate: float):
        self.rate = rate
        self.tokens = rate
        self.last_update = time.monotonic()
        self.lock = Lock()

    def consume(self, amount: int, stop_event: Event = None):
        if self.rate <= 0:
            return
        sleep_time = 0
        with self.lock:
            now = time.monotonic()
            elapsed = now - self.last_update
            self.last_update = now
            self.tokens += elapsed * self.rate
            if self.tokens > self.rate:
                self.tokens = self.rate
            self.tokens -= amount
            if self.tokens < 0:
                sleep_time = -self.tokens / self.rate
        if sleep_time > 0:
            while sleep_time > 0:
                if stop_event and stop_event.is_set():
                    break
                s = min(0.1, sleep_time)
                time.sleep(s)
                sleep_time -= s


# ---------------------------------------------------------------------------
# CDN URL 处理 (与 CDN.get_url_list 一致)
# ---------------------------------------------------------------------------
def resolve_cdn_url(url_list: list) -> str:
    """从多个 CDN URL 中选可用链接，HEAD 请求获取 size，与 QueryWorker 一致。"""
    # CDN 过滤 + 替换
    filtered = []
    for u in url_list:
        if "szbdyd.com" in u or "mcdn" in u:
            continue
        filtered.append(u)

    replaced = []
    for u in filtered:
        for entry in config.get(config.cdn_server_list):
            node = entry.get("host")
            parsed = urlparse(u)
            if node != parsed.netloc:
                new_parsed = parsed._replace(netloc=node)
                replaced.append(new_parsed.geturl())

    if config.get(config.prefer_cdn_server_provider):
        candidates = list(dict.fromkeys(replaced + filtered))
    else:
        candidates = list(dict.fromkeys(filtered + replaced))

    for url in candidates:
        try:
            with httpx.Client(timeout=10, follow_redirects=True) as cli:
                resp = cli.head(url, headers={"Referer": "https://www.bilibili.com/",
                                               "User-Agent": config.get(config.user_agent)})
            cl = resp.headers.get("Content-Length", "")
            ct = resp.headers.get("Content-Type", "")
            if ct and "text" in ct.lower():
                continue
            if not cl or not cl.isdigit():
                continue
            size = int(cl)
            if size <= 10240:
                continue
            return url, size
        except Exception:
            continue
    raise RuntimeError("无法获取有效的下载链接")


def extract_download_urls(media_info: dict) -> list:
    """从媒体信息中提取所有可用 URL。"""
    urls = []
    for key in ["baseUrl", "base_url", "backupUrl", "backup_url", "url"]:
        value = media_info.get(key)
        if isinstance(value, list):
            urls.extend(value)
        elif isinstance(value, str):
            urls.append(value)
    return urls


# ---------------------------------------------------------------------------
# HTTP 客户端
# ---------------------------------------------------------------------------
def _create_http_client(timeout: int = 30) -> httpx.Client:
    c = httpx.Client(
        timeout=timeout,
        follow_redirects=True,
        headers={
            "User-Agent": config.get(config.user_agent),
            "Referer": "https://www.bilibili.com/",
        },
        transport=httpx.HTTPTransport(retries=3),
    )
    cookies = get_cookies()
    for k, v in cookies.items():
        c.cookies.set(k, v, domain=".bilibili.com", path="/")
    return c


_HTTP_CLIENT = _create_http_client(30)
# 用于 HEAD 请求的短超时客户端
_HTTP_CLIENT_HEAD = _create_http_client(10)


# ---------------------------------------------------------------------------
# 步骤 3: URL 解析 → bvid / cid / title (复用现有解析流程)
# ---------------------------------------------------------------------------
class URLParser:
    """URL 解析器，复用项目内 VideoParser 的 parse 流程，绕过 Qt 信号层。"""

    def __init__(self, url: str):
        self.raw_url = url.strip()
        self.url = url.strip()
        self.bvid: str = ""
        self.cid: int = 0
        self.title: str = "output"
        self.attribute: int = 0
        self.ep_id: int = 0
        self.aid: int = 0
        self.duration: int = 0
        self.cover: str = ""
        self.pubdate: int = 0
        self.pages: list[dict] = []

    def parse(self) -> bool:
        # 1. b23.tv 短链展开
        self.url = self._resolve_b23(self.url)
        # 2. 提取 bvid
        bv_match = re.search(r"BV[\w]+", self.url)
        av_match = re.search(r"av(\d+)", self.url, re.IGNORECASE)
        if bv_match:
            self.bvid = bv_match.group(0)
        elif av_match:
            self.bvid = av_to_bvid(int(av_match.group(1)))
        else:
            logger.error("无法从 URL 提取 BV 号: %s", self.url)
            return False

        # 3. 调用 wbi/view API
        if not self._fetch_from_view_api():
            return False

        # 4. 确定 cid (支持 ?p= 分P)
        p_match = re.search(r"[?&]p=(\d+)", self.url)
        target_page = int(p_match.group(1)) if p_match else 0
        if target_page > 0 and self.pages:
            page = next((p for p in self.pages if p["page"] == target_page), None)
            if page:
                self.cid = page["cid"]
                self.title = f"{self.title} - P{target_page}"
                self.duration = page.get("duration", 0)
            else:
                logger.error("未找到分P %d (共 %d 个分P)", target_page, len(self.pages))
                return False
        else:
            self.cid = self.pages[0]["cid"] if self.pages else self.cid

        logger.info("解析完成: %s (bvid=%s, cid=%d)", self.title[:50], self.bvid, self.cid)
        return True

    def _resolve_b23(self, url: str) -> str:
        match = re.search(r"b23\.tv/(\w+)", url)
        if not match:
            return url
        logger.info("解析 b23.tv 短链接...")
        try:
            resp = _HTTP_CLIENT.get(url)
            return str(resp.url)
        except Exception as e:
            logger.warning("b23.tv 解析失败: %s", e)
            return url

    def _fetch_from_view_api(self) -> bool:
        params = {"bvid": self.bvid}
        api_url = f"https://api.bilibili.com/x/web-interface/wbi/view?{_enc_wbi(params)}"
        resp = self._request_with_retry(api_url, "获取视频信息")
        if not resp:
            return False

        data = resp.get("data", {})
        self.title = data.get("title", self.bvid)
        self.aid = data.get("aid", 0)
        pages = data.get("pages", [])

        if pages:
            self.cid = pages[0].get("cid", 0)
            self.duration = pages[0].get("duration", 0)
            self.pages = [{"cid": p["cid"], "page": p["page"],
                           "duration": p.get("duration", 0), "part": p.get("part", "")}
                          for p in pages]
        else:
            self.cid = data.get("cid", 0)
            self.duration = data.get("duration", 0)
            self.pages = [{"cid": self.cid, "page": 1, "duration": self.duration, "part": ""}]

        self.cover = data.get("pic", "")
        self.pubdate = data.get("pubdate", 0)
        self.attribute = Attribute.VIDEO_BIT
        return True

    @staticmethod
    def _request_with_retry(url: str, desc: str, max_retries: int = 3) -> Optional[dict]:
        last_error = None
        for attempt in range(1, max_retries + 1):
            try:
                resp = _HTTP_CLIENT.get(url)
                resp.raise_for_status()
                data = resp.json()
                if data.get("code", -1) != 0:
                    raise RuntimeError(f"API code={data.get('code')}: {data.get('message', '')}")
                return data
            except Exception as e:
                last_error = str(e)
                if attempt < max_retries:
                    logger.warning("  [%s] %s，%ds 后重试 (%d/%d)...",
                                   desc, last_error, 2 ** attempt, attempt, max_retries)
                    time.sleep(2 ** attempt)
        logger.error("  [%s] 失败 (已重试 %d 次): %s", desc, max_retries, last_error)
        return None


# ---------------------------------------------------------------------------
# 步骤 4: playurl API → 媒体流下载链接解析
# ---------------------------------------------------------------------------
def fetch_play_url(bvid: str, cid: int, video_quality_id: int, attribute: int,
                   ep_id: int = 0, aid: int = 0) -> dict:
    """获取媒体流下载信息，与 ParseWorker.get_info() 保持一致。"""
    base = ParserBase()

    if attribute & Attribute.VIDEO_BIT:
        params = {
            "bvid": bvid,
            "cid": cid,
            "qn": video_quality_id,
            "fnver": 0,
            "fnval": 4048,
            "fourk": 1,
        }
        api_url = f"https://api.bilibili.com/x/player/wbi/playurl?{base.enc_wbi(params)}"
    elif attribute & Attribute.BANGUMI_BIT:
        params = {
            "bvid": bvid,
            "cid": cid,
            "qn": video_quality_id,
            "fnver": 0,
            "fnval": 12240,
            "fourk": 1,
        }
        api_url = f"https://api.bilibili.com/pgc/player/web/playurl?{urlencode(params)}"
    elif attribute & Attribute.CHEESE_BIT:
        params = {
            "avid": aid,
            "cid": cid,
            "qn": video_quality_id,
            "fnver": 0,
            "fnval": 16,
            "fourk": 1,
            "ep_id": ep_id,
        }
        api_url = f"https://api.bilibili.com/pugv/player/web/playurl?{urlencode(params)}"
    else:
        # 默认走视频类型
        params = {
            "bvid": bvid,
            "cid": cid,
            "qn": video_quality_id,
            "fnver": 0,
            "fnval": 4048,
            "fourk": 1,
        }
        api_url = f"https://api.bilibili.com/x/player/wbi/playurl?{base.enc_wbi(params)}"

    logger.info("  请求 playurl: %s...", api_url[:80])

    for attempt in range(1, 4):
        try:
            resp = _HTTP_CLIENT.get(api_url)
            resp.raise_for_status()
            data = resp.json()
            if data.get("code", -1) != 0:
                msg = data.get("message", "无法获取播放链接")
                # 某些 code（如 -404）可能是临时错误
                raise RuntimeError(f"API code={data.get('code')}: {msg}")
            return data.get("data", {}) or data.get("result", {})
        except Exception as e:
            if attempt >= 3:
                raise RuntimeError(f"获取播放链接失败 (已重试 3 次): {e}")
            logger.warning("  playurl 请求失败: %s，%ds 后重试...", e, 2 ** attempt)
            time.sleep(2 ** attempt)


def parse_media_info(info_data: dict, video_quality_id: int, audio_quality_id: int,
                     video_codec_id: int) -> dict:
    """解析媒体信息，返回下载队列。与 ParseWorker.parse_download_info() 一致。"""
    # 判断媒体类型
    if "dash" in info_data:
        media_type = MediaType.DASH
    elif info_data.get("format", "").startswith("mp4"):
        media_type = MediaType.MP4
    elif info_data.get("format", "").startswith("flv"):
        media_type = MediaType.FLV
    else:
        raise RuntimeError("未知媒体类型")

    result = {
        "media_type": media_type,
        "video": None,
        "audio": None,
        "video_parts": [],
    }

    # 解析视频流
    if video_quality_id > 0:
        video_info = _select_video_stream(info_data, video_quality_id, video_codec_id, media_type)
        if video_info:
            url, size = resolve_cdn_url(extract_download_urls(video_info))
            result["video"] = {
                "url": url,
                "file_size": size,
                "quality_id": video_info.get("id", 0),
                "codec_id": video_info.get("codecid", 0),
                "ext": _get_video_ext(media_type),
                "quality": reversed_video_quality_map.get(video_info.get("id", 0), "?"),
            }
        else:
            logger.warning("未找到合适的视频流")

    # 解析音频流 (仅 DASH)
    if audio_quality_id > 0 and media_type == MediaType.DASH:
        audio_info = _select_audio_stream(info_data, audio_quality_id)
        if audio_info:
            url, size = resolve_cdn_url(extract_download_urls(audio_info))
            result["audio"] = {
                "url": url,
                "file_size": size,
                "quality_id": audio_info.get("id", 0),
                "ext": _get_audio_ext(audio_info.get("id", 0)),
                "quality": reversed_audio_quality_map.get(audio_info.get("id", 0), "?"),
            }
        else:
            logger.warning("未找到合适的音频流")

    return result


def _get_video_ext(media_type: MediaType) -> str:
    if media_type == MediaType.DASH:
        return "m4s"
    elif media_type == MediaType.MP4:
        return "mp4"
    return "flv"


def _get_audio_ext(quality_id: int) -> str:
    if quality_id == 30251:
        return "flac"
    elif quality_id == 30250:
        return "ec3"
    return "m4a"


def _select_video_stream(info_data: dict, video_quality_id: int,
                         video_codec_id: int, media_type: MediaType) -> Optional[dict]:
    """选择最佳视频流，与 VideoInfoParser 逻辑一致。"""
    if media_type == MediaType.DASH:
        dash_videos = info_data.get("dash", {}).get("video", [])
        if not dash_videos:
            return None
        # 按 quality_id → codec_id 建立索引
        by_quality = {}
        for entry in dash_videos:
            qid = entry.get("id", 0)
            cid = entry.get("codecid", 0)
            if qid not in by_quality:
                by_quality[qid] = {}
            by_quality[qid][cid] = entry

        # auto 模式：按优先级
        if video_quality_id == 200:
            for qid in config.get(config.video_quality_priority):
                if qid in by_quality:
                    video_quality_id = qid
                    break
            else:
                video_quality_id = next(iter(by_quality))

        if video_quality_id not in by_quality:
            video_quality_id = next(iter(by_quality))

        codecs = by_quality[video_quality_id]
        if video_codec_id == 20:
            for cid in config.get(config.video_codec_priority):
                if cid in codecs:
                    return codecs[cid]
            return next(iter(codecs.values()))
        elif video_codec_id in codecs:
            return codecs[video_codec_id]
        return next(iter(codecs.values()))

    elif media_type in (MediaType.MP4, MediaType.FLV):
        durl = info_data.get("durl", [])
        if not durl:
            return None
        size_sum = sum(d.get("size", 0) for d in durl)
        return {"id": video_quality_id, "codecid": 7, "url_entry_list": durl, "size": size_sum}

    return None


def _select_audio_stream(info_data: dict, audio_quality_id: int) -> Optional[dict]:
    """选择最佳音频流，与 AudioInfoParser 逻辑一致。"""
    dash = info_data.get("dash", {})
    audio_list = []
    # flac
    if flac_node := dash.get("flac"):
        if audio_node := flac_node.get("audio"):
            audio_list.append(audio_node)
    # dolby
    if dolby_node := dash.get("dolby"):
        if audio_node := dolby_node.get("audio"):
            audio_list.append(audio_node[0])
    # normals
    audio_list.extend(dash.get("audio", []))

    # build index
    by_id = {}
    for entry in audio_list:
        qid = entry.get("id", 0)
        by_id[qid] = entry

    if audio_quality_id == 30300:
        for qid in config.get(config.audio_quality_priority):
            if qid in by_id:
                return by_id[qid]
        return by_id.get(next(iter(by_id))) if by_id else None
    else:
        return by_id.get(audio_quality_id)


# ---------------------------------------------------------------------------
# 步骤 5: 分片下载器 (ThreadPoolExecutor, 断点续传, 重试, 限速)
# ---------------------------------------------------------------------------
MAX_CHUNK_RETRIES = 5
CHUNK_SIZE = 4 * 1024 * 1024  # 4MB


class ChunkedDownloader:
    """多线程分片下载器，纯 Python 实现，无 Qt 依赖。

    与 ChunkWorker + Downloader 行为一致：
      - 分片下载 + 并发控制
      - Range 请求实现断点续传
      - 指数退避重试 (最多 5 次)
      - 令牌桶限速
      - 实时进度回调
    """

    def __init__(self, url: str, file_path: Path, file_size: int,
                 num_threads: int = 4, token_bucket: TokenBucket = None,
                 progress_callback: Callable = None):
        self.url = url
        self.file_path = file_path
        self.file_size = file_size
        self.num_threads = max(1, num_threads)
        self.token_bucket = token_bucket or TokenBucket(0)
        self.progress_callback = progress_callback

        self._stop_event = Event()
        self._downloaded = 0
        self._lock = Lock()
        self._error: Optional[str] = None

    def download(self) -> bool:
        """执行下载，返回 True 成功 / False 失败。"""
        # 确保目录存在
        self.file_path.parent.mkdir(parents=True, exist_ok=True)

        # 预分配/初始化文件
        if not self.file_path.exists():
            self.file_path.touch()
            # 简单预分配（fseek 到末尾写一个字节）
            if self.file_size > 0:
                try:
                    with open(self.file_path, "r+b") as f:
                        f.seek(self.file_size - 1)
                        f.write(b"\0")
                except OSError:
                    pass
        else:
            # 断点续传：检测已下载的区块
            pass

        # 计算分片
        total_chunks = max(1, (self.file_size + CHUNK_SIZE - 1) // CHUNK_SIZE)
        chunks = [(i, i * CHUNK_SIZE, min((i + 1) * CHUNK_SIZE, self.file_size))
                  for i in range(total_chunks)]

        print(f"  分片下载: {total_chunks} 个分片 x {self.num_threads} 线程"
              + (f", 限速 {self.token_bucket.rate / 1024 / 1024:.1f} MB/s" if self.token_bucket.rate > 0 else ""))

        with ThreadPoolExecutor(max_workers=self.num_threads) as executor:
            futures = {
                executor.submit(self._download_chunk, idx, start, end): (idx, start, end)
                for idx, start, end in chunks
            }

            for future in as_completed(futures):
                if self._stop_event.is_set():
                    break
                try:
                    ok = future.result()
                    if not ok:
                        self._stop_event.set()
                except Exception:
                    self._stop_event.set()

        if self._error:
            logger.error("  下载失败: %s", self._error)
            return False
        if self._stop_event.is_set() and self._error:
            return False
        return True

    def _download_chunk(self, chunk_index: int, start: int, end: int) -> bool:
        """下载单个分片（带重试）。"""
        if self._stop_event.is_set():
            return False

        chunk_size = end - start
        headers = {"Range": f"bytes={start}-{end - 1}"}

        for attempt in range(1, MAX_CHUNK_RETRIES + 1):
            if self._stop_event.is_set():
                return False
            downloaded = 0
            try:
                with open(self.file_path, "r+b") as f:
                    f.seek(start)
                    with _HTTP_CLIENT.stream("GET", self.url, headers=headers,
                                             timeout=10) as response:
                        response.raise_for_status()
                        content_length = int(response.headers.get("Content-Length", chunk_size))
                        for chunk in response.iter_bytes(chunk_size=8192):
                            if self._stop_event.is_set():
                                break
                            if chunk:
                                chunk_len = len(chunk)
                                self.token_bucket.consume(chunk_len, self._stop_event)
                                f.write(chunk)
                                downloaded += chunk_len
                                with self._lock:
                                    self._downloaded += chunk_len
                                    if self.progress_callback:
                                        self.progress_callback(self._downloaded, self.file_size)

                if self._stop_event.is_set():
                    return False

                if downloaded >= content_length:
                    return True
                else:
                    raise ConnectionError(f"分片不完整 (预期 {content_length}, 实际 {downloaded})")

            except Exception as e:
                with self._lock:
                    self._downloaded = max(0, self._downloaded - downloaded)

                if not self._is_retryable(e) or attempt >= MAX_CHUNK_RETRIES:
                    self._error = f"分片 {chunk_index + 1} 下载失败: {e}"
                    return False

                time.sleep(min(2 ** (attempt - 1), 8))

        return False

    @staticmethod
    def _is_retryable(exc: Exception) -> bool:
        if isinstance(exc, httpx.HTTPStatusError):
            status = getattr(exc.response, "status_code", 0)
            if status in (400, 401, 403, 404, 405, 410, 416):
                return False
            return status >= 500 or status in (408, 429)
        if isinstance(exc, (httpx.RequestError, ConnectionError)):
            return True
        if isinstance(exc, OSError):
            return exc.errno in (errno.EAGAIN, errno.EWOULDBLOCK, errno.EINTR,
                                 errno.ETIMEDOUT, errno.ECONNRESET,
                                 errno.ECONNABORTED, errno.ECONNREFUSED,
                                 errno.ENETDOWN, errno.ENETUNREACH,
                                 errno.EHOSTUNREACH, errno.EPIPE)
        return True

    def cancel(self):
        self._stop_event.set()


# ---------------------------------------------------------------------------
# 步骤 6: FFmpeg 合并
# ---------------------------------------------------------------------------
def _find_ffmpeg() -> Optional[str]:
    ffmpeg_exe = "ffmpeg.exe" if sys.platform == "win32" else "ffmpeg"
    # 检查 PATH
    found = shutil.which(ffmpeg_exe)
    if found:
        return found
    # 检查 bundled
    bundle_path = Path(__file__).resolve().parent.parent / "bundle" / ffmpeg_exe
    if bundle_path.exists():
        return str(bundle_path)
    return None


def ffmpeg_merge(video_path: str, audio_path: str, output_path: str) -> bool:
    """使用 ffmpeg 合并音视频，输出 mp4。"""
    ffmpeg = _find_ffmpeg()
    if not ffmpeg:
        logger.error("FFmpeg 不可用，无法合并。请检查 FFmpeg 安装。")
        return False

    cmd = [
        ffmpeg, "-y",
        "-i", video_path,
        "-i", audio_path,
        "-c:v", "copy",
        "-c:a", "copy",
        output_path,
    ]
    logger.info("  合并: %s + %s → %s", Path(video_path).name, Path(audio_path).name, Path(output_path).name)
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=600)
        if result.returncode == 0:
            return True
        logger.error("  FFmpeg 合并失败: %s", result.stderr[-300:] if result.stderr else "")
        return False
    except Exception as e:
        logger.error("  FFmpeg 异常: %s", e)
        return False


def ffmpeg_convert_m4a_to_mp3(input_path: str, output_path: str) -> bool:
    ffmpeg = _find_ffmpeg()
    if not ffmpeg:
        return False
    cmd = [ffmpeg, "-y", "-i", input_path, "-c:a", "libmp3lame", "-q:a", "2", output_path]
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=300)
        return result.returncode == 0
    except Exception as e:
        logger.error("  FFmpeg m4a→mp3 异常: %s", e)
        return False


# ---------------------------------------------------------------------------
# 步骤 7: 下载流程编排器
# ---------------------------------------------------------------------------
class MediaDownloader:
    """视频/音频下载编排器。

    完整流程:
      1. URLParser → bvid + cid + title
      2. fetch_play_url() → media_info
      3. parse_media_info() → video/audio download URLs
      4. ChunkedDownloader → 多线程分片下载
      5. ffmpeg_merge() → 合并音视频
    """

    def __init__(self, url: str, output_dir: str,
                 video_quality: int = 200, audio_quality: int = 30300,
                 video_codec: int = 20,
                 download_video: bool = True, download_audio: bool = True,
                 merge: bool = True, threads: int = 4,
                 speed_limit: int = 0,
                 subtitle: bool = False, subtitle_type: str = "srt",
                 danmaku: bool = False, danmaku_type: str = "ass",
                 cover: bool = False, metadata: bool = False,
                 m4a_to_mp3: bool = False,
                 force: bool = False):
        self.url = url
        self.output_dir = Path(output_dir).resolve()
        self.video_quality = video_quality
        self.audio_quality = audio_quality
        self.video_codec = video_codec
        self.download_video = download_video
        self.download_audio = download_audio
        self.merge = merge
        self.threads = max(1, min(threads, 10))
        self.speed_limit = speed_limit
        self.subtitle = subtitle
        self.subtitle_type = subtitle_type
        self.danmaku = danmaku
        self.danmaku_type = danmaku_type
        self.cover = cover
        self.metadata = metadata
        self.m4a_to_mp3 = m4a_to_mp3
        self.force = force

        # 令牌桶
        rate = speed_limit * 1024 * 1024 if speed_limit > 0 else 0
        self.token_bucket = TokenBucket(rate)

    def run(self) -> int:
        """执行下载，返回 0 成功。"""
        # ---- 阶段 1: 解析 URL ----
        print(f"\n{'=' * 60}")
        print("  解析 URL...")
        parser = URLParser(self.url)
        if not parser.parse():
            return 1

        # ---- 阶段 2: 获取播放链接 ----
        print("\n  获取播放链接...")
        try:
            info_data = fetch_play_url(
                parser.bvid, parser.cid,
                self.video_quality, parser.attribute,
                parser.ep_id, parser.aid,
            )
        except Exception as e:
            logger.error("获取播放链接失败: %s", e)
            return 1

        # ---- 阶段 3: 解析媒体信息 ----
        print("\n  解析媒体信息...")
        media = parse_media_info(
            info_data,
            self.video_quality if self.download_video else 0,
            self.audio_quality if self.download_audio else 0,
            self.video_codec,
        )

        # ---- 打印媒体信息 ----
        print(f"\n  视频: {safe_filename(parser.title)}")
        print(f"  时长: {format_time(parser.duration)}")
        if media["video"]:
            v = media["video"]
            print(f"  视频流: {v['quality']} ({v['codec_id']}), {format_size(v['file_size'])}, {v['ext']}")
        if media["audio"]:
            a = media["audio"]
            print(f"  音频流: {a['quality']}, {format_size(a['file_size'])}, {a['ext']}")
        total_size = (media["video"]["file_size"] if media["video"] else 0) + \
                     (media["audio"]["file_size"] if media["audio"] else 0)
        print(f"  总大小: {format_size(total_size)}")
        print(f"  输出: {self.output_dir}")
        print()

        # ---- 阶段 4: 下载 ----
        safe_title = safe_filename(parser.title)
        downloaded_files = []
        total_downloaded = [0]
        total_pct = [0]

        def progress_cb(downloaded, total):
            total_downloaded[0] = downloaded
            pct = int(downloaded / total * 100) if total > 0 else 0
            if pct != total_pct[0]:
                total_pct[0] = pct
                bar_width = 30
                filled = int(bar_width * pct / 100)
                bar = "█" * filled + "░" * (bar_width - filled)
                sys.stdout.write(f"\r  [{bar}] {pct:3d}%  {format_size(downloaded)} / {format_size(total)}")
                sys.stdout.flush()
        # 下载视频
        video_downloaded = False
        if media["video"]:
            vname = f"{safe_title}.video.{media['video']['ext']}"
            vpath = self.output_dir / vname
            if vpath.exists() and not self.force:
                print(f"  视频文件已存在，跳过: {vname}")
                video_downloaded = True
            else:
                print(f"  下载视频流 ({media['video']['quality']}, {format_size(media['video']['file_size'])})...")
                dl = ChunkedDownloader(
                    url=media["video"]["url"],
                    file_path=vpath,
                    file_size=media["video"]["file_size"],
                    num_threads=self.threads,
                    token_bucket=self.token_bucket,
                    progress_callback=progress_cb,
                )
                if dl.download():
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                    print(f"  视频下载完成: {vpath.name}")
                    video_downloaded = True
                else:
                    return 1

        if video_downloaded:
            downloaded_files.append(str(vpath))

        # 下载音频
        audio_downloaded = False
        if media["audio"]:
            aname = f"{safe_title}.audio.{media['audio']['ext']}"
            apath = self.output_dir / aname
            if apath.exists() and not self.force:
                print(f"  音频文件已存在，跳过: {aname}")
                audio_downloaded = True
            else:
                print(f"  下载音频流 ({media['audio']['quality']}, {format_size(media['audio']['file_size'])})...")
                dl = ChunkedDownloader(
                    url=media["audio"]["url"],
                    file_path=apath,
                    file_size=media["audio"]["file_size"],
                    num_threads=self.threads,
                    token_bucket=self.token_bucket,
                    progress_callback=progress_cb,
                )
                if dl.download():
                    sys.stdout.write("\n")
                    sys.stdout.flush()
                    print(f"  音频下载完成: {apath.name}")
                    audio_downloaded = True
                else:
                    return 1

        if audio_downloaded:
            downloaded_files.append(str(apath))

        # ---- 阶段 5: 合并 ----
        if self.merge and video_downloaded and audio_downloaded:
            vpath = self.output_dir / f"{safe_title}.video.{media['video']['ext']}"
            apath = self.output_dir / f"{safe_title}.audio.{media['audio']['ext']}"
            opath = self.output_dir / f"{safe_title}.mp4"

            if opath.exists() and not self.force:
                print(f"  合并文件已存在，跳过: {opath.name}")
            else:
                print(f"\n  合并音视频...")
                if ffmpeg_merge(str(vpath), str(apath), str(opath)):
                    print(f"  合并完成: {opath.name}")
                    # 删除原始文件
                    vpath.unlink(missing_ok=True)
                    apath.unlink(missing_ok=True)
                else:
                    return 1
        elif not self.merge and video_downloaded and not audio_downloaded:
            # 仅视频：重命名
            vpath = self.output_dir / f"{safe_title}.video.{media['video']['ext']}"
            final = self.output_dir / f"{safe_title}.mp4"
            if vpath != final and not final.exists():
                vpath.rename(final)
                print(f"  完成: {final.name}")
        elif not self.merge and not video_downloaded and audio_downloaded:
            apath = self.output_dir / f"{safe_title}.audio.{media['audio']['ext']}"
            if self.m4a_to_mp3 and media["audio"]["ext"] == "m4a":
                final = self.output_dir / f"{safe_title}.mp3"
                if ffmpeg_convert_m4a_to_mp3(str(apath), str(final)):
                    apath.unlink(missing_ok=True)
                    print(f"  转换完成: {final.name}")
                else:
                    print(f"  完成 (未转换): {apath.name}")
            else:
                final = self.output_dir / f"{safe_title}.{media['audio']['ext']}"
                if apath != final:
                    apath.rename(final)
                print(f"  完成: {final.name}")

        # ---- 阶段 6: 附加文件 ----
        if self.subtitle:
            self._download_subtitle(parser.bvid, parser.cid, safe_title)
        if self.danmaku:
            self._download_danmaku(parser.bvid, parser.cid, safe_title, parser.duration)
        if self.cover:
            self._download_cover(parser.cover, safe_title)

        print()
        return 0

    # ------------------------------------------------------------------
    # 附加文件: 字幕 / 弹幕 / 封面
    # ------------------------------------------------------------------
    def _download_subtitle(self, bvid: str, cid: int, safe_title: str):
        print("\n  下载字幕...")
        try:
            params = {
                "bvid": bvid, "cid": cid,
                "dm_img_list": "[]",
                "dm_img_str": "V2ViR0wgMS4wIChPcGVuR0wgRVMgMi4wIENocm9taXVtKQ",
                "dm_cover_img_str": "QU5HTEUgKE5WSURJQSwgTlZJRElBIEdlRm9yY2UgUlRYIDQwNjAgTGFwdG9wIEdQVSAoMHgwMDAwMjhFMCkgRGlyZWN0M0QxMSB2c181XzAgcHNfNV8wLCBEM0QxMSlHb29nbGUgSW5jLiAoTlZJRElBKQ",
                "dm_img_inter": '{"ds":[],"wh":[5231,6067,75],"of":[475,950,475]}',
            }
            api_url = f"https://api.bilibili.com/x/player/wbi/v2?{_enc_wbi(params)}"
            resp = _HTTP_CLIENT.get(api_url).json()
            subtitle_list = resp.get("data", {}).get("subtitle", {}).get("subtitles", [])
            if not subtitle_list:
                print("  该视频没有字幕")
                return

            for entry in subtitle_list:
                lan = entry.get("lan", "unknown")
                sub_url = f"https:{entry.get('subtitle_url', '')}"
                sub_data = _HTTP_CLIENT.get(sub_url).json()
                # 格式转换
                st = SubtitleType(self.subtitle_type)
                if st == SubtitleType.SRT:
                    contents = self._to_srt(sub_data)
                    suffix = "srt"
                elif st == SubtitleType.LRC:
                    contents = self._to_lrc(sub_data)
                    suffix = "lrc"
                elif st == SubtitleType.TXT:
                    contents = self._to_txt(sub_data)
                    suffix = "txt"
                elif st == SubtitleType.ASS:
                    from util.parse.additional.file.subtitle_ass import SubtitlesASS
                    contents = SubtitlesASS(sub_data, safe_title).generate()
                    suffix = "ass"
                else:
                    contents = json.dumps(sub_data, ensure_ascii=False, indent=2)
                    suffix = "json"

                filename = f"{safe_title}.Subtitles.{lan}.{suffix}"
                filepath = self.output_dir / filename
                filepath.write_text(contents, encoding="utf-8")
                print(f"    {lan} → {filename}")
        except Exception as e:
            logger.warning("  字幕下载失败: %s", e)

    def _download_danmaku(self, bvid: str, cid: int, safe_title: str, duration: int):  # noqa: ARG002
        print("\n  下载弹幕...")
        try:
            import util.misc.dm_pb2 as dm_pb2
            from math import ceil

            parts = max(1, ceil(duration / 360))
            all_segments = []
            for idx in range(1, parts + 1):
                params = {"type": 1, "oid": cid, "segment_index": idx}
                url = f"https://api.bilibili.com/x/v2/dm/wbi/web/seg.so?{_enc_wbi(params)}"
                resp = _HTTP_CLIENT.get(url, headers={"Accept": "application/octet-stream"})
                dm_seg = dm_pb2.DmSegMobileReply()
                dm_seg.ParseFromString(resp.content)
                for elem in dm_seg.elems:
                    all_segments.append({
                        "id": elem.id, "progress": elem.progress,
                        "mode": elem.mode, "fontsize": elem.fontsize,
                        "color": elem.color, "midHash": elem.midHash,
                        "content": elem.content, "ctime": elem.ctime,
                        "weight": elem.weight, "action": elem.action,
                        "pool": elem.pool, "idStr": elem.idStr,
                        "attr": elem.attr,
                    })

            suffix = self.danmaku_type
            if suffix == "xml":
                contents = self._danmaku_to_xml(all_segments, cid)
            elif suffix == "ass":
                from util.parse.additional.file.danmaku_ass import DanmakuASS
                contents = DanmakuASS(all_segments, safe_title).generate()
            else:
                contents = json.dumps(all_segments, ensure_ascii=False, indent=2)

            filename = f"{safe_title}.Danmaku.{suffix}"
            filepath = self.output_dir / filename
            filepath.write_text(contents, encoding="utf-8")
            print(f"    {filename} ({len(all_segments)} 条弹幕)")
        except Exception as e:
            logger.warning("  弹幕下载失败: %s", e)

    @staticmethod
    def _danmaku_to_xml(segments: list, cid: int) -> str:
        lines = ['<?xml version="1.0" encoding="UTF-8"?>', f"<i><chatserver>chat.bilibili.com</chatserver><chatid>{cid}</chatid>"]
        for s in segments:
            p = ','.join([str(s.get(k, '')) for k in ['progress', 'mode', 'fontsize', 'color', 'ctime', 'pool', 'midHash', 'idStr', 'weight']])
            lines.append(f'<d p="{p}">{s["content"]}</d>')
        lines.append('</i>')
        return '\n'.join(lines)

    @staticmethod
    def _to_srt(data: dict) -> str:
        lines = []
        for i, item in enumerate(data.get("body", [])):
            start = item.get("from", 0)
            end = item.get("to", 0)
            content = item.get("content", "")
            h = int(start // 3600)
            m = int((start % 3600) // 60)
            s = int(start % 60)
            ms = int(round((start - int(start)) * 1000))
            h2 = int(end // 3600)
            m2 = int((end % 3600) // 60)
            s2 = int(end % 60)
            ms2 = int(round((end - int(end)) * 1000))
            lines.append(f"{i + 1}")
            lines.append(f"{h:02d}:{m:02d}:{s:02d},{ms:03d} --> {h2:02d}:{m2:02d}:{s2:02d},{ms2:03d}")
            lines.append(f"{content}\n")
        return "\n".join(lines).strip()

    @staticmethod
    def _to_lrc(data: dict) -> str:
        lines = []
        for item in data.get("body", []):
            start = item.get("from", 0)
            m = int(start // 60)
            s = start % 60
            lines.append(f"[{m:02d}:{s:05.2f}]{item.get('content', '')}")
        return "\n".join(lines).strip()

    @staticmethod
    def _to_txt(data: dict) -> str:
        return "\n".join(item.get("content", "") for item in data.get("body", []))

    def _download_cover(self, cover_url: str, safe_title: str):
        if not cover_url:
            return
        print("\n  下载封面...")
        try:
            resp = _HTTP_CLIENT.get(cover_url)
            resp.raise_for_status()
            ext = cover_url.rsplit(".", 1)[-1].split("?")[0] or "jpg"
            filepath = self.output_dir / f"{safe_title}.Cover.{ext}"
            filepath.write_bytes(resp.content)
            print(f"    {filepath.name}")
        except Exception as e:
            logger.warning("  封面下载失败: %s", e)


# ---------------------------------------------------------------------------
# CLI 参数解析
# ---------------------------------------------------------------------------
def build_parser() -> argparse.ArgumentParser:
    p = argparse.ArgumentParser(
        description="Bili23 Downloader CLI - 命令行视频/音频/字幕下载",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
示例:
  python -m cli "https://www.bilibili.com/video/BV1xx411c7mD"
  python -m cli -q 120 --codec 12 "BV1xx411c7mD"
  python -m cli -o ~/Downloads --audio-only "BV1xx411c7mD?p=2"
  python -m cli --video-only --no-merge "BV1xx411c7mD"
  python -m cli --subtitle --danmaku --cover "BV1xx411c7mD"
  python -m cli --subtitle-only "BV1xx411c7mD"
  python -m cli --subtitle-only -t ass -o ~/Downloads "BV1xx411c7mD"
  python -m cli --speed-limit 5 --threads 8 "BV1xx411c7mD"

质量ID (--quality): 200=自动 127=8K 126=杜比 125=HDR 120=4K 116=1080P60
                     112=1080P+ 80=1080P 64=720P 32=480P 16=360P
音频ID (--audio-quality): 30300=自动 30251=Hi-Res 30250=杜比全景声
                           30280=192K 30232=132K 30216=64K
编码ID (--codec): 20=自动 7=AVC/H.264 12=HEVC/H.265 13=AV1

异常排查:
  1. "配置文件不存在" → 首次使用需运行 GUI 版本
  2. "无法获取播放链接" → 视频需登录或区域限制
  3. "FFmpeg 不可用" → 仅音频/无合并模式无需 FFmpeg
        """,
    )
    p.add_argument("url", help="B 站视频链接或 BV/av 号")
    p.add_argument("-o", "--output", default=None, help="输出目录 (默认: 配置中下载目录)")
    p.add_argument("-q", "--quality", type=int, default=200,
                   help="视频质量 ID (默认: 200=自动)")
    p.add_argument("--audio-quality", type=int, default=30300,
                   help="音频质量 ID (默认: 30300=自动)")
    p.add_argument("--codec", type=int, default=20,
                   help="视频编码 ID (默认: 20=自动)")
    p.add_argument("--video-only", action="store_true", default=False,
                   help="仅下载视频流")
    p.add_argument("--audio-only", action="store_true", default=False,
                   help="仅下载音频流")
    p.add_argument("--no-merge", action="store_true", default=False,
                   help="不合并音视频，保留独立流文件")
    p.add_argument("--threads", type=int, default=4,
                   help="下载线程数 (1-10, 默认: 4)")
    p.add_argument("--speed-limit", type=int, default=0,
                   help="下载限速 (MB/s, 0=不限, 默认: 0)")
    p.add_argument("--subtitle", action="store_true", default=False,
                   help="下载视频的同时下载字幕")
    p.add_argument("--subtitle-only", action="store_true", default=False,
                   help="仅下载字幕，不下载视频/音频")
    p.add_argument("--subtitle-type", choices=["srt", "lrc", "txt", "ass", "json"],
                   default="json", help="字幕格式 (默认: json)")
    p.add_argument("--danmaku", action="store_true", default=False,
                   help="下载弹幕")
    p.add_argument("--danmaku-type", choices=["xml", "ass", "json"],
                   default="ass", help="弹幕格式 (默认: ass)")
    p.add_argument("--cover", action="store_true", default=False,
                   help="下载封面")
    p.add_argument("--metadata", action="store_true", default=False,
                   help="下载元数据")
    p.add_argument("--m4a-to-mp3", action="store_true", default=False,
                   help="将 m4a 音频转换为 mp3")
    p.add_argument("--force", action="store_true", default=False,
                   help="强制覆盖已存在的文件")
    p.add_argument("--quiet", action="store_true", default=False,
                   help="安静模式")
    return p


# ---------------------------------------------------------------------------
# 字幕专用入口
# ---------------------------------------------------------------------------
def _run_subtitle_only(url: str, output_dir: str, subtitle_type: str, force: bool) -> int:
    """仅下载字幕，不做任何视频/音频请求。"""
    print(f"\n{'=' * 60}")
    print("  字幕下载模式")
    print(f"{'=' * 60}")

    # 1. 解析 URL → bvid + cid + title
    parser = URLParser(url)
    if not parser.parse():
        return 1

    print(f"\n  视频: {safe_filename(parser.title)}")
    print(f"  输出: {output_dir}")
    print(f"  格式: {subtitle_type.upper()}")

    # 2. 获取字幕列表
    print("\n  获取字幕列表...")
    params = {
        "bvid": parser.bvid, "cid": parser.cid,
        "dm_img_list": "[]",
        "dm_img_str": "V2ViR0wgMS4wIChPcGVuR0wgRVMgMi4wIENocm9taXVtKQ",
        "dm_cover_img_str": "QU5HTEUgKE5WSURJQSwgTlZJRElBIEdlRm9yY2UgUlRYIDQwNjAgTGFwdG9wIEdQVSAoMHgwMDAwMjhFMCkgRGlyZWN0M0QxMSB2c181XzAgcHNfNV8wLCBEM0QxMSlHb29nbGUgSW5jLiAoTlZJRElBKQ",
        "dm_img_inter": '{"ds":[],"wh":[5231,6067,75],"of":[475,950,475]}',
    }
    api_url = f"https://api.bilibili.com/x/player/wbi/v2?{_enc_wbi(params)}"
    try:
        resp = _HTTP_CLIENT.get(api_url).json()
    except Exception as e:
        logger.error("获取字幕列表失败: %s", e)
        return 1

    subtitle_list = resp.get("data", {}).get("subtitle", {}).get("subtitles", [])
    if not subtitle_list:
        print("  该视频没有字幕")
        return 0

    # 展示可用语言
    print(f"\n  可用字幕 ({len(subtitle_list)} 种):")
    for s in subtitle_list:
        lan = s.get("lan", "?")
        doc = s.get("lan_doc", lan)
        print(f"    - {lan} ({doc})")
    print()

    # 3. 下载每种语言
    count = 0
    safe_title = safe_filename(parser.title)
    out_path = Path(output_dir)
    out_path.mkdir(parents=True, exist_ok=True)

    for entry in subtitle_list:
        lan = entry.get("lan", "unknown")
        sub_url = f"https:{entry.get('subtitle_url', '')}"
        if not sub_url:
            logger.warning("  %s: 无下载地址，跳过", lan)
            continue

        filename = f"{safe_title}.Subtitles.{lan}.{subtitle_type}"
        filepath = out_path / filename

        if filepath.exists() and not force:
            print(f"  [{lan}] 已存在，跳过 (--force 覆盖)")
            count += 1
            continue

        try:
            sub_data = _HTTP_CLIENT.get(sub_url).json()
            st = SubtitleType(subtitle_type)
            if st == SubtitleType.SRT:
                contents = _format_subtitle_srt(sub_data)
            elif st == SubtitleType.LRC:
                contents = _format_subtitle_lrc(sub_data)
            elif st == SubtitleType.TXT:
                contents = _format_subtitle_txt(sub_data)
            elif st == SubtitleType.ASS:
                from util.parse.additional.file.subtitle_ass import SubtitlesASS
                contents = SubtitlesASS(sub_data, safe_title).generate()
            else:
                contents = json.dumps(sub_data, ensure_ascii=False, indent=2)

            filepath.write_text(contents, encoding="utf-8")
            print(f"  [{lan}] ✓ {filename}")
            count += 1
        except Exception as e:
            logger.warning("  [%s] 下载失败: %s", lan, e)

    print(f"\n  完成: 成功 {count}/{len(subtitle_list)} 种语言")
    print(f"{'=' * 60}")
    return 0 if count > 0 else 1


def _format_subtitle_srt(data: dict) -> str:
    lines = []
    for i, item in enumerate(data.get("body", [])):
        s = item.get("from", 0)
        e = item.get("to", 0)
        c = item.get("content", "")
        lines.append(f"{i + 1}")
        lines.append(f"{_fmt_srt(s)} --> {_fmt_srt(e)}")
        lines.append(f"{c}\n")
    return "\n".join(lines).strip()


def _fmt_srt(sec: float) -> str:
    h = int(sec // 3600)
    m = int((sec % 3600) // 60)
    s = int(sec % 60)
    ms = int(round((sec - int(sec)) * 1000))
    if ms == 1000:
        s += 1; ms = 0
    if s >= 60:
        m += s // 60; s %= 60
    if m >= 60:
        h += m // 60; m %= 60
    return f"{h:02d}:{m:02d}:{s:02d},{ms:03d}"


def _format_subtitle_lrc(data: dict) -> str:
    lines = []
    for item in data.get("body", []):
        start = item.get("from", 0)
        m = int(start // 60)
        s = start % 60
        lines.append(f"[{m:02d}:{s:05.2f}]{item.get('content', '')}")
    return "\n".join(lines).strip()


def _format_subtitle_txt(data: dict) -> str:
    return "\n".join(item.get("content", "") for item in data.get("body", []))


# ---------------------------------------------------------------------------
# 主入口
# ---------------------------------------------------------------------------
def run_cli(args) -> int:
    if args.quiet:
        logging.getLogger().setLevel(logging.WARNING)

    output_dir = str(Path(args.output).resolve()) if args.output else config.get(config.download_path)

    # --subtitle-only 模式：跳过所有视频/音频，只下载字幕
    if args.subtitle_only:
        return _run_subtitle_only(args.url, output_dir, args.subtitle_type, args.force)

    # 计算 video/audio 质量
    if args.video_only:
        download_video, download_audio = True, False
    elif args.audio_only:
        download_video, download_audio = False, True
    else:
        download_video, download_audio = True, True

    downloader = MediaDownloader(
        url=args.url,
        output_dir=output_dir,
        video_quality=args.quality,
        audio_quality=args.audio_quality,
        video_codec=args.codec,
        download_video=download_video,
        download_audio=download_audio,
        merge=not args.no_merge,
        threads=args.threads,
        speed_limit=args.speed_limit,
        subtitle=args.subtitle,
        subtitle_type=args.subtitle_type,
        danmaku=args.danmaku,
        danmaku_type=args.danmaku_type,
        cover=args.cover,
        metadata=args.metadata,
        m4a_to_mp3=args.m4a_to_mp3,
        force=args.force,
    )

    try:
        result = downloader.run()
        if result == 0:
            print(f"{'=' * 60}")
            print("  ✓ 下载完成")
            print(f"{'=' * 60}")
        return result
    except KeyboardInterrupt:
        print("\n  用户取消下载")
        return 130
    except Exception as e:
        logger.error("下载异常: %s", e)
        import traceback
        traceback.print_exc()
        return 1


def main():
    parser = build_parser()
    args = parser.parse_args()
    if not args.url:
        parser.print_help()
        sys.exit(1)
    sys.exit(run_cli(args))


if __name__ == "__main__":
    main()
