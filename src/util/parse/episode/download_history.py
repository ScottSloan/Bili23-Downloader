from ...download.task.hash_id import calc_episode_hash_id, is_identifiable
from ...download.task.manager import task_manager
from ...common.config import config

from .tree import TreeItem, Attribute

from typing import List
import logging

logger = logging.getLogger(__name__)

def mark_download_history(nodes: List[TreeItem]):
    """
    查询下载记录，把其中已有的条目标记为 in_download_history

    必须在解析线程里、节点交给 GUI 线程之前调用：此后节点归 GUI 线程所有，
    再从这里改字段就是跨线程写。

    直接解析出的条目，判定口径与创建任务时的重复下载判定完全一致（同一个 hash_id、
    同样查两张表），保证列表上打了勾的条目，点下载时也必然被判为重复。

    需要二次解析的稿件条目（收藏夹、个人空间、合集列表、稍后再看、历史记录）
    解析时没有 cid，改为按 bvid 统计下载记录中的分P数。点下载时二次解析出的
    各分P仍会逐个走 hash 判重，这里只决定列表上显不显示对勾。
    """
    # 关闭时连查询一并省掉，上千条的收藏夹、个人空间每一页都要查一次库
    if not config.get(config.parse_list_mark_downloaded):
        return

    candidates: dict[str, List[TreeItem]] = {}
    # 需要二次解析的稿件条目，按 bvid 匹配
    reparse_candidates: dict[str, List[TreeItem]] = {}

    for node in nodes:
        for leaf in node.get_all_leaves():
            if leaf.attribute & Attribute.TREE_NODE_BIT:
                continue

            if leaf.attribute & Attribute.NEED_PARSE_BIT:
                # 这类条目此刻缺少 cid，算不出与入库端一致的 hash，只能按 bvid 找。
                # 只认稿件：番剧二次解析按 ep_id 取单集，条目上的 bvid 未必是那一集的；
                # 课程则会整季下载，一个条目对应不上具体的任务
                if _is_reparse_video(leaf):
                    reparse_candidates.setdefault(leaf.bvid, []).append(leaf)

                continue

            if not is_identifiable(leaf.attribute):
                continue

            # 经由 to_dict() 计算，与创建任务时走的是同一份输入
            candidates.setdefault(calc_episode_hash_id(leaf.to_dict()), []).append(leaf)

    # 两类查询各自兜底：bvid 查询依赖 SQLite 的 JSON 函数，它失败不该连累按 hash 的标记
    if candidates:
        try:
            existing = task_manager.db_manager.filter_existing_hash_ids(candidates.keys())

        except Exception:
            # 标记只是辅助信息，查不出来也不能让解析失败
            logger.exception("查询下载记录失败，解析列表将不显示已下载标记")

            existing = set()

        for hash_id in existing:
            for leaf in candidates[hash_id]:
                leaf.in_download_history = True

    if reparse_candidates:
        try:
            part_counts = task_manager.db_manager.count_parts_by_bvid(reparse_candidates.keys())

        except Exception:
            logger.exception("按 bvid 查询下载记录失败，需要二次解析的条目将不显示已下载标记")

            part_counts = {}

        for bvid, part_count in part_counts.items():
            for leaf in reparse_candidates.get(bvid, []):
                # 已知分P总数时，只下过其中一部分的不打勾：对勾表示"全部下载过"。
                # 未知时只能以"有记录"为准 —— 二次解析总是为全部分P一并建任务，
                # 只有用户另行直接解析该稿件、只勾了部分分P时才会出现缺漏
                if leaf.page_count and part_count < leaf.page_count:
                    continue

                leaf.in_download_history = True

def _is_reparse_video(leaf: TreeItem):
    return bool(leaf.bvid) and leaf.attribute & Attribute.VIDEO_BIT and not leaf.attribute & (Attribute.BANGUMI_BIT | Attribute.CHEESE_BIT)
