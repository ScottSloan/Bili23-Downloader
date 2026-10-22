from ...common._json import dumps_stable
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

def calc_hash_id(attribute: int, aid = None, bvid = None, cid = None, ep_id = None, sid = None, task_id = None, course_id = None, lesson_id = None, item_id = None, section_id = None):
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

    course_id = _to_int(course_id)
    lesson_id = _to_int(lesson_id)
    item_id = _to_int(item_id)
    section_id = _to_int(section_id)

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

    elif attribute & Attribute.LESSON_BIT:
        metadata = {
            "course_id": course_id,
            "lesson_id": lesson_id,
            "item_id": item_id,
            "section_id": section_id
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

    return hashlib.md5(dumps_stable(metadata).encode("utf-8")).hexdigest()

def calc_episode_hash_id(episode_info: dict):
    """
    根据解析结果（TreeItem.to_dict() 的产物）计算 hash_id

    创建任务时的重复判定与解析列表的"已下载"标记都走这里，二者必须对同一个条目
    算出同一个值，否则列表上打了勾的条目点下载时却不被判为重复（或者反过来）
    """
    return calc_hash_id(
        episode_info.get("attribute", 0),
        aid = episode_info.get("aid"),
        bvid = episode_info.get("bvid"),
        cid = episode_info.get("cid"),
        ep_id = episode_info.get("ep_id"),
        sid = episode_info.get("sid"),
        course_id = episode_info.get("course_id"),
        lesson_id = episode_info.get("lesson_id"),
        item_id = episode_info.get("item_id"),
        section_id = episode_info.get("section_id")
    )

def is_identifiable(attribute: int):
    """
    条目的 hash_id 能否唯一指向一个媒体，即能否命中 calc_hash_id 中的具名分支

    落到兜底分支的条目在解析端没有 task_id 可以区分，彼此会算出相同的 hash，
    拿它去查下载记录只会误报，因此一律视为无法判定
    """
    return bool(_to_int(attribute) & (Attribute.VIDEO_BIT | Attribute.BANGUMI_BIT | Attribute.LESSON_BIT | Attribute.CHEESE_BIT | Attribute.AUDIO_BIT))
