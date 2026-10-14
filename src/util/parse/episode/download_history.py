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

    判定口径与创建任务时的重复下载判定完全一致（同一个 hash_id、同样查两张表），
    保证列表上打了勾的条目，点下载时也必然被判为重复。
    """
    # 关闭时连查询一并省掉，上千条的收藏夹、个人空间每一页都要查一次库
    if not config.get(config.parse_list_mark_downloaded):
        return

    candidates: dict[str, List[TreeItem]] = {}

    for node in nodes:
        for leaf in node.get_all_leaves():
            # 需要二次解析的条目（收藏夹、个人空间等）此刻缺少 cid，且二次解析后
            # 一个分P视频会拆成多个任务，算出的 hash 与入库时的对不上，只能跳过
            if leaf.attribute & (Attribute.TREE_NODE_BIT | Attribute.NEED_PARSE_BIT):
                continue

            if not is_identifiable(leaf.attribute):
                continue

            # 经由 to_dict() 计算，与创建任务时走的是同一份输入
            candidates.setdefault(calc_episode_hash_id(leaf.to_dict()), []).append(leaf)

    if not candidates:
        return

    try:
        existing = task_manager.db_manager.filter_existing_hash_ids(candidates.keys())

    except Exception:
        # 标记只是辅助信息，查不出来也不能让解析失败
        logger.exception("查询下载记录失败，解析列表将不显示已下载标记")

        return

    for hash_id in existing:
        for leaf in candidates[hash_id]:
            leaf.in_download_history = True
