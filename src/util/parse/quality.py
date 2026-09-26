from ..common.data import video_codec_prefix_map

from .parser.base import build_video_info_url

import logging

logger = logging.getLogger(__name__)

# 部分老稿件（例如 1080P60 是后来单独补转码的）的 playurl 响应并不完整：
# 请求 qn >= 116 时 dash.video 里只有 116 一档，请求 qn < 116 时才返回 80 及以下的档位，
# 两组流互斥，任何参数组合都无法一次取全（qn 全谱、fnval、platform、老接口均已实测排除）。
#
# 好在 support_formats 始终声明了全部档位，且每档的 codecs 与该档实际提供的编码完全一致，
# 因此画质、编码列表一律以 support_formats 为准，真正的流则等到用户选定某一档时再按需补取。
# 绝大多数稿件一次请求就能拿全，只有这类稿件在选中缺失档位时才会多发一次请求。

def parse_declared_quality_map(info_data: dict):
    """
    从 support_formats 解析出「画质档位 -> 可用编码列表」，按画质从高到低排列。

    support_formats 缺失时返回 None，由调用方回退到以 dash.video 为准的原有逻辑
    （番剧、课程等接口的响应结构与视频接口并不一致）。
    """
    support_formats = info_data.get("support_formats")
    video_list = (info_data.get("dash") or {}).get("video") or []

    if not support_formats or not video_list:
        return None

    # support_formats 会把大会员专享、付费等当前账号取不到的档位一并声明出来。
    # 请求 qn=127 时服务端给出的最高档就是这个账号的权限上限，
    # 高于它的声明一律不列入，否则界面上会出现选了也下不了的画质
    highest_quality_id = max(entry.get("id") for entry in video_list if isinstance(entry.get("id"), int))

    declared_map = {}

    for entry in support_formats:
        if not isinstance(entry, dict):
            continue

        quality_id = entry.get("quality")

        if not isinstance(quality_id, int) or quality_id > highest_quality_id:
            continue

        codec_id_list = []

        for codecs in entry.get("codecs") or []:
            codec_id = video_codec_prefix_map.get(str(codecs).split(".")[0])

            if codec_id is not None and codec_id not in codec_id_list:
                codec_id_list.append(codec_id)

        declared_map[quality_id] = codec_id_list

    if not declared_map:
        return None

    return dict(sorted(declared_map.items(), key = lambda item: item[0], reverse = True))

def fetch_video_streams(bvid: str, cid: int, quality_id: int):
    """
    按指定画质补取 dash 视频流，失败时返回空列表，调用方沿用已有的流即可
    """
    from ..network.request import SyncNetWorkRequest

    try:
        response = SyncNetWorkRequest(build_video_info_url(bvid, cid, quality_id)).run()

        if response.get("code") != 0:
            logger.warning("按需补取 qn=%s 的视频流失败: %s", quality_id, response.get("message"))
            return []

        return ((response.get("data") or {}).get("dash") or {}).get("video") or []

    except Exception:
        logger.warning("按需补取 qn=%s 的视频流失败", quality_id, exc_info = True)
        return []

def merge_video_streams(video_info_map: dict, stream_list: list):
    """
    把补取到的流并入 video_info_map，返回是否有新增
    """
    updated = False

    for entry in stream_list:
        quality_id = entry.get("id")
        codec_id = entry.get("codecid")

        if quality_id is None or codec_id is None:
            continue

        if not video_info_map[quality_id][codec_id]:
            video_info_map[quality_id][codec_id] = entry.copy()
            updated = True

    return updated
