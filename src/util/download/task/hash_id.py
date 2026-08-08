from ...common._json import json_dumps_stable
from ...parse.episode.tree import Attribute

import hashlib

# hash_id 算法版本。仅在算法本身发生变化时递增，用于触发数据库中已有记录的重算。
HASH_ID_VERSION = 1

def _to_int(value) -> int:
    # TaskInfo 中 aid/cid/ep_id/sid 均为 int 且默认为 0，而解析结果中缺失这些键时取到的是 None。
    # 不归一化就会让同一个视频在解析端与入库端算出两个不同的 hash。
    try:
        return int(value) if value else 0

    except (TypeError, ValueError):
        return 0

def _to_str(value) -> str:
    return str(value) if value else ""

def calc_hash_id(attribute: int, aid = None, bvid = None, cid = None, ep_id = None, sid = None, task_id = None):
    """
    根据媒体的唯一标识计算 hash_id，用于重复下载判定

    此结果会随任务一并入库，解析端与入库端必须使用完全相同的算法，
    因此统一收敛到这一个函数，避免两处实现随时间产生分歧。
    """
    attribute = _to_int(attribute)

    aid = _to_int(aid)
    cid = _to_int(cid)
    ep_id = _to_int(ep_id)
    sid = _to_int(sid)
    bvid = _to_str(bvid)
    task_id = _to_str(task_id)

    if attribute & Attribute.VIDEO_BIT:
        # 投稿视频
        metadata = {
            "bvid": bvid,
            "cid": cid,
            "aid": aid
        }

    elif attribute & Attribute.BANGUMI_BIT:
        # 剧集类
        metadata = {
            "bvid": bvid,
            "cid": cid,
            "aid": aid,
            "ep_id": ep_id
        }

    elif attribute & Attribute.CHEESE_BIT:
        # 课程类
        metadata = {
            "aid": aid,
            "cid": cid,
            "ep_id": ep_id
        }

    elif attribute & Attribute.AUDIO_BIT:
        # 音乐类
        metadata = {
            "sid": sid
        }

    else:
        # 属性缺失或未知时同样要给出可区分的 hash，否则会抛出异常中断任务创建与数据库迁移。
        # 入库端会带上 task_id，使这类无法识别的记录彼此唯一，从而不会被误判为重复。
        metadata = {
            "aid": aid,
            "bvid": bvid,
            "cid": cid,
            "ep_id": ep_id,
            "sid": sid,
            "task_id": task_id
        }

    return hashlib.md5(json_dumps_stable(metadata).encode("utf-8")).hexdigest()
