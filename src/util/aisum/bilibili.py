"""
B 站内容下载适配器

根据 BV 号下载字幕 JSON / 音频流 / 视频流到 AISum 目录。
"""

from pathlib import Path
import logging
import urllib.parse
import time as _time
from functools import reduce
from hashlib import md5

from util.common.config import config
from util.network.request import SyncNetWorkRequest, ResponseType, client

logger = logging.getLogger(__name__)

# ---- Bilibili API 常量 ----
API_VIDEO_INFO = "https://api.bilibili.com/x/web-interface/view"
HEADERS_REFERER = {"Referer": "https://www.bilibili.com/"}

# WBI 签名混音表（对齐 ParserBase.mixinKeyEncTab）
_MIXIN_KEY_ENC_TAB = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52
]


def _get_aisum_dir() -> Path:
    """获取 AISum 下载目录"""
    download_path = config.get(config.download_path)
    d = Path(download_path) / "AISum"
    d.mkdir(parents=True, exist_ok=True)
    return d


def _extract_bvid(url: str) -> str:
    """从 URL 或纯 BV 号中提取 BV 号"""
    import re
    # 纯 BV 号
    m = re.match(r"^(BV[a-zA-Z0-9]+)$", url)
    if m:
        return m.group(1)
    # URL 中的 BV 号
    m = re.search(r"(BV[a-zA-Z0-9]+)", url)
    if m:
        return m.group(1)
    raise ValueError(f"无法从输入中提取 BV 号: {url}")


def _get_video_info(bvid: str) -> dict:
    """调用 B 站 API 获取视频基本信息（WBI 签名）"""
    up_headers()
    params = {"bvid": bvid}
    url = f"https://api.bilibili.com/x/web-interface/wbi/view?{_enc_wbi(params)}"
    resp = SyncNetWorkRequest(
        url=url,
        response_type=ResponseType.JSON,
    ).run()
    code = resp.get("code", -1)
    if code != 0:
        raise RuntimeError(f"获取视频信息失败: {resp.get('message', '未知错误')} (code={code})")
    return resp["data"]


def _get_cid(bvid: str) -> int:
    """获取视频的 cid"""
    up_headers()
    info = _get_video_info(bvid)
    cid = info.get("cid")
    if not cid:
        # 多 P 视频尝试从 pages 获取
        pages = info.get("pages", [])
        if pages:
            cid = pages[0].get("cid")
    if not cid:
        raise RuntimeError("无法获取视频 cid")
    return cid


def up_headers():
    """更新请求头"""
    client.headers.update({
        "Referer": "https://www.bilibili.com/",
        "User-Agent": config.get(config.user_agent),
    })


def _enc_wbi(params: dict) -> str:
    """WBI 签名（对齐 ParserBase.enc_wbi）"""
    def get_mixin_key(orig: str) -> str:
        return reduce(lambda s, i: s + orig[i], _MIXIN_KEY_ENC_TAB, "")[:32]

    mixin_key = get_mixin_key(
        config.get(config.img_key) + config.get(config.sub_key)
    )
    curr_time = round(_time.time())
    params["wts"] = curr_time
    params = dict(sorted(params.items()))
    params = {
        k: "".join(filter(lambda ch: ch not in "!'()*", str(v)))
        for k, v in params.items()
    }
    query = urllib.parse.urlencode(params)
    wbi_sign = md5((query + mixin_key).encode()).hexdigest()
    params["w_rid"] = wbi_sign
    return urllib.parse.urlencode(params)


# ============================================================
# 字幕下载
# ============================================================
def _get_subtitle_list(bvid: str, cid: int) -> list:
    """通过 WBI 签名 API 获取字幕列表（对齐 SubtitlesParser._get_subtitles_url_list）"""
    up_headers()
    params = {
        "bvid": bvid,
        "cid": cid,
        "dm_img_list": "[]",
        "dm_img_str": "V2ViR0wgMS4wIChPcGVuR0wgRVMgMi4wIENocm9taXVtKQ",
        "dm_cover_img_str": "QU5HTEUgKE5WSURJQSwgTlZJRElBIEdlRm9yY2UgUlRYIDQwNjAgTGFwdG9wIEdQVSAoMHgwMDAwMjhFMCkgRGlyZWN0M0QxMSB2c181XzAgcHNfNV8wLCBEM0QxMSlHb29nbGUgSW5jLiAoTlZJRElBKQ",
        "dm_img_inter": '{"ds":[],"wh":[5231,6067,75],"of":[475,950,475]}',
    }
    url = f"https://api.bilibili.com/x/player/wbi/v2?{_enc_wbi(params)}"
    resp = SyncNetWorkRequest(
        url=url,
        response_type=ResponseType.JSON,
    ).run()
    data = resp.get("data", {})
    if data.get("need_login_subtitle"):
        raise RuntimeError("该视频字幕需要登录才能获取，请先在 App 中登录 B 站账号")
    return data.get("subtitle", {}).get("subtitles", [])


def _select_best_subtitle(subtitles: list) -> dict:
    """优先选择人工字幕，同类型中优先中文（对齐 SubtitlesParser 逻辑）"""
    if not subtitles:
        return {}

    human = [s for s in subtitles
             if "自动" not in s.get("lan_doc", "")]
    ai = [s for s in subtitles if "自动" in s.get("lan_doc", "")]

    for group in (human, ai):
        for lang_pref in ("中文", "Chinese", "zh-CN", "zh-Hans", "zh", "chi"):
            for s in group:
                if lang_pref in s.get("lan_doc", ""):
                    return s
        if group:
            return group[0]
    return {}


def _get_video_meta(bvid: str, title: str = "", desc: str = "") -> str:
    """获取视频元数据并保存为 _meta.txt"""
    if not title or not desc:
        info = _get_video_info(bvid)
        title = info.get("title", "")
        desc = info.get("desc", "") or info.get("description", "")

    meta_path = _get_aisum_dir() / f"{bvid}_meta.txt"
    with open(meta_path, "w", encoding="utf-8") as f:
        f.write(f"title={title}\n")
        f.write(f"desc={desc}\n")
    logger.info(f"元数据已保存: {meta_path}")
    return str(meta_path)


def download_subtitle(url_or_bvid: str) -> tuple:
    """下载字幕 JSON 并保存，返回 (json_path, meta_path)"""
    import json as _json

    bvid = _extract_bvid(url_or_bvid)
    cid = _get_cid(bvid)

    # 获取视频元数据
    info = _get_video_info(bvid)
    title = info.get("title", "")
    desc = info.get("desc", "") or info.get("description", "")
    meta_path = _get_video_meta(bvid, title, desc)

    # 获取字幕列表并选择最优
    subtitles = _get_subtitle_list(bvid, cid)
    best = _select_best_subtitle(subtitles)
    if not best:
        raise RuntimeError("该视频没有字幕")

    sub_url = best.get("subtitle_url", "")
    if not sub_url:
        raise RuntimeError("无法获取字幕 URL")
    if sub_url.startswith("//"):
        sub_url = "https:" + sub_url
    elif not sub_url.startswith(("http://", "https://")):
        sub_url = "https://" + sub_url

    up_headers()
    resp = SyncNetWorkRequest(
        url=sub_url,
        response_type=ResponseType.RESPONSE,
    ).run()
    resp.raise_for_status()
    sub_json = resp.json()

    # 保存清洗后的 JSON（去除非关键字段）
    try:
        body = sub_json.get("body", [])
        if not body:
            raise RuntimeError("字幕文件内容为空")
    except Exception:
        raise RuntimeError("字幕文件格式无效")

    json_path = _get_aisum_dir() / f"{bvid}_subtitle.json"
    with open(json_path, "w", encoding="utf-8") as f:
        _json.dump(sub_json, f, ensure_ascii=False, indent=2)

    logger.info(f"字幕 JSON 已下载: {json_path} (来源: {best.get('lan_doc', '未知')})")
    return str(json_path), meta_path


def download_audio(url_or_bvid: str) -> str:
    """下载音频流（返回 m4a 文件路径）"""
    bvid = _extract_bvid(url_or_bvid)
    cid = _get_cid(bvid)

    dest = _get_aisum_dir() / f"{bvid}_audio.m4a"

    # 请求 DASH 流地址（WBI 签名，fnval=4048 获取 dash 流）
    up_headers()
    params = {"bvid": bvid, "cid": cid, "qn": 30280, "fnval": 4048, "fourk": 1}
    url = f"https://api.bilibili.com/x/player/wbi/playurl?{_enc_wbi(params)}"
    resp = SyncNetWorkRequest(
        url=url,
        response_type=ResponseType.JSON,
    ).run()
    code = resp.get("code", -1)
    if code != 0:
        raise RuntimeError(f"获取播放地址失败: {resp.get('message', '')}")

    dash = resp.get("data", {}).get("dash")
    if not dash:
        raise RuntimeError("该视频没有 DASH 流")

    audios = dash.get("audio", [])
    if not audios:
        raise RuntimeError("没有可用的音频流")

    # 取最高码率音频
    audio = sorted(audios, key=lambda x: x.get("bandwidth", 0), reverse=True)[0]
    audio_url = audio.get("baseUrl") or audio.get("base_url", "")
    if not audio_url:
        raise RuntimeError("无法获取音频 URL")

    _download_file(audio_url, dest)
    logger.info(f"音频已下载: {dest}")
    return str(dest)


def download_video(url_or_bvid: str) -> str:
    """下载视频流（返回 mp4 文件路径）"""
    bvid = _extract_bvid(url_or_bvid)
    cid = _get_cid(bvid)

    dest = _get_aisum_dir() / f"{bvid}_video.mp4"

    up_headers()
    params = {"bvid": bvid, "cid": cid, "qn": 80, "fnval": 4048, "fourk": 1}
    url = f"https://api.bilibili.com/x/player/wbi/playurl?{_enc_wbi(params)}"
    resp = SyncNetWorkRequest(
        url=url,
        response_type=ResponseType.JSON,
    ).run()
    code = resp.get("code", -1)
    if code != 0:
        raise RuntimeError(f"获取播放地址失败: {resp.get('message', '')}")

    dash = resp.get("data", {}).get("dash")
    if not dash:
        raise RuntimeError("该视频没有 DASH 流")

    videos = dash.get("video", [])
    if not videos:
        raise RuntimeError("没有可用的视频流")

    # 取最低画质视频（节省流量）
    video = sorted(videos, key=lambda x: x.get("bandwidth", 0))[0]
    video_url = video.get("baseUrl") or video.get("base_url", "")
    if not video_url:
        raise RuntimeError("无法获取视频 URL")

    _download_file(video_url, dest)
    logger.info(f"视频已下载: {dest}")
    return str(dest)


def _download_file(url: str, dest: Path):
    """使用 httpx 下载文件到指定路径（支持范围请求/续传）"""
    import httpx

    up_headers()
    cookies = dict(client.cookies)
    headers = dict(client.headers)

    with open(dest, "wb") as f:
        with httpx.stream("GET", url, headers=headers, cookies=cookies,
                           timeout=300, follow_redirects=True) as resp:
            resp.raise_for_status()
            for chunk in resp.iter_bytes(chunk_size=8192):
                f.write(chunk)
