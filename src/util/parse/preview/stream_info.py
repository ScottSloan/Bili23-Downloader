"""
按选定的档位查这一路流的详情 —— 不依赖 Qt

桌面版这件事由 `video_info.py` / `audio_info.py` 做，但那两个类是 `QObject`，
查询走 `AsyncTask` + 信号回 GUI 线程，**在 WebUI 进程里用不了**（D16：那边没有
Qt 事件循环，跨线程信号会静默不投递）。

真正干活的几块本来就是无 Qt 的同步代码：档位定位在 `quality_base.py` 的两个基类里，
取流走 `parse/quality.py` 的 `fetch_video_streams`，文件大小走
`network/download_url.py` 的 `resolve_download_url`。这里把 `QueryInfoWorker.run()`
那套同步逻辑重写一遍，只是把信号换成了返回值。

## 状态从 PreviewerInfo 上取

`PreviewSession` 自己只持有两个档位映射表，`info_data` / `media_type` / `bvid` / `cid`
都写在全局的 `PreviewerInfo` 上（桌面版整个预览流程都建在它上面，搬走牵动面太大）。
所以**这些函数必须在 `PreviewSession` 刚 preview 过、且仍持有 `_preview_lock` 的时候调**
—— 换个视频预览一次，全局就被覆盖了。调用入口收敛在 `session.py` 的
`preview_stream()` 里，不要从别处直接调这里的函数。
"""

from typing import Optional
import logging
import re

from ...common.config import config
from ...common.enum import MediaType
from ...network.download_url import resolve_download_url
from ...network.request import SyncNetWorkRequest

from ..quality import fetch_video_streams, merge_video_streams

from .info import PreviewerInfo

logger = logging.getLogger(__name__)

# 与桌面版一致：小于这个大小的响应不认作有效的视频流
MIN_FILE_SIZE = 10240

def _download_urls(media_info: dict) -> list:
    """把流信息里各种写法的地址都收集起来"""
    urls = []

    for key in ("baseUrl", "base_url", "backupUrl", "backup_url", "url"):
        value = media_info.get(key)

        if isinstance(value, list):
            urls.extend(value)

        elif isinstance(value, str):
            urls.append(value)

    return urls

def _durl_list(response: dict) -> list:
    """mp4 / flv 的分段列表，剧集与投稿的结构不同"""
    match PreviewerInfo.info_data.get("parser_type"):
        case "bangumi":
            return response.get("result", {}).get("durl", []) or []

        case _:
            return response.get("data", {}).get("durl", []) or []

def _mp4_file_size(quality_id: int) -> tuple:
    """
    mp4 / flv 走 durl 列表累加，返回 (文件大小, 时长)

    **按正则替换 qn 而不是匹配固定值**：预览请求用的档位会变，
    写死字面量会在请求档位调整之后悄悄失效（与桌面版同一处理）
    """
    query_url = PreviewerInfo.info_data.get("query_url") or ""

    if not query_url:
        return 0, 0

    url = re.sub(r"([?&])qn=\d+", rf"\g<1>qn={quality_id}", query_url)

    response = SyncNetWorkRequest(url).run()

    size = 0
    length = 0

    for entry in _durl_list(response):
        size += entry.get("size", 0)
        length += entry.get("length", 0)

    return size, length

def _resolve_target(video, video_quality_id: int, video_codec_id: int):
    """
    把「用户选的档位」落到实际可用的画质与编码上

    与桌面版 `VideoInfoParser.resolve_target()` 逐行等价 —— 那个方法长在 QObject 上，
    这里只用得到基类的几个纯函数（可用档位列表、可用编码列表、两个按优先级挑选），
    所以照搬一份。**两边必须给出同一个结果**，否则「桌面下到 4K、网页下到 1080P」

    200 / 20 分别是画质与编码的「自动」，此时按用户配置的优先级挑
    """
    if not video.available_quality_list:
        return None, None

    if video_quality_id == 200:
        video_quality_id = video.get_video_quality_id_by_priority()

    elif video_quality_id not in video.available_quality_list:
        video_quality_id = video.available_quality_list[0]

    codec_list = video.get_available_codec_list(video_quality_id)

    if not codec_list:
        return None, None

    if video_codec_id == 20 or video_codec_id not in codec_list:
        video_codec_id = video.get_video_codec_id_by_priority(video_quality_id)

    return video_quality_id, video_codec_id

def _audio_media_info(audio, audio_quality_id: int) -> dict:
    """
    取某一档音质的流。30300 是「自动」，按用户配置的优先级挑第一个有的

    与桌面版 `AudioInfoParser.get_audio_info()` 等价
    """
    if audio_quality_id != 30300:
        return audio.audio_quality_info_map.get(audio_quality_id, {})

    for quality_id in config.get(config.audio_quality_priority):
        if quality_id in audio.audio_quality_info_map:
            return audio.audio_quality_info_map.get(quality_id, {})

    return {}

def video_stream_info(session, video_quality_id: int, video_codec_id: int) -> Optional[dict]:
    """
    某个画质 + 编码下的视频流详情

    返回 None 表示这一类没有视频流可查（需要二次解析的节点、纯音频等）。

    返回里一律是**裸数值**，格式化交给前端：服务端进程没有 Qt 的翻译函数，
    在这里拼好字符串下发的话，中文界面上会冒出英文单位（D12）
    """
    video = session.video

    quality_id, codec_id = _resolve_target(video, video_quality_id, video_codec_id)

    if quality_id is None:
        return None

    media_type = PreviewerInfo.media_type
    media_info = video.video_info_map.get(quality_id, {}).get(codec_id) or {}

    if not media_info and media_type == MediaType.DASH:
        # 少数稿件的首次响应只包含请求的那一档，缺的档位要按需补取。
        # 补到的整组流并回映射表，接着切到同组的其它编码时就不必再请求一次
        stream_list = fetch_video_streams(PreviewerInfo.bvid, PreviewerInfo.cid, quality_id)

        matched = [entry for entry in stream_list if entry.get("id") == quality_id]

        if not matched:
            raise RuntimeError("无法获取该清晰度的视频流")

        merge_video_streams(video.video_info_map, stream_list)

        media_info = next(
            (entry for entry in matched if entry.get("codecid") == codec_id), matched[0])

    if not media_info:
        return None

    media_info = dict(media_info)

    file_size = 0
    timelength = media_info.get("timelength", 0)

    match media_type:
        case MediaType.DASH | MediaType.M4A:
            # m4a 借用 dash 那条路：虽然只有一个档位，文件大小仍然要查
            result = resolve_download_url(_download_urls(media_info),
                                          min_file_size = MIN_FILE_SIZE)

            file_size = result["file_size"]

        case MediaType.MP4 | MediaType.FLV:
            file_size, extra = _mp4_file_size(quality_id)

            timelength = timelength + extra

    return {
        "quality_id": quality_id,
        "codec_id": codec_id,
        "frame_rate": str(media_info.get("frame_rate", "")),
        "bitrate": media_info.get("bandwidth", 0),
        "file_size": file_size,
        # mp4 / flv 的响应可能只给试看片段；dash 一定是完整的
        "is_full_video": _is_full_video(media_type, timelength),
    }

def _is_full_video(media_type, timelength: int) -> bool:
    if media_type in (MediaType.MP4, MediaType.FLV):
        return PreviewerInfo.info_data.get("timelength") == timelength

    return True

def audio_stream_info(session, audio_quality_id: int) -> Optional[dict]:
    """
    某个音质下的音频流详情

    返回 None 表示这一路没有音频流 —— 可能是无声视频（dash），
    也可能是音轨已经并在视频流里（mp4 / flv）。两者的说法不同，
    由调用方按 `media_type` 区分，与桌面版 `on_query_audio_info` 一致
    """
    media_info = _audio_media_info(session.audio, audio_quality_id)

    if not media_info:
        return None

    result = resolve_download_url(_download_urls(media_info), min_file_size = MIN_FILE_SIZE)

    return {
        "quality_id": media_info.get("id", audio_quality_id),
        "codec": media_info.get("codecs", ""),
        "bitrate": media_info.get("bandwidth", 0),
        "file_size": result["file_size"],
    }
