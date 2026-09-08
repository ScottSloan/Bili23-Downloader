"""
链接解析（S3-11）

解析链路一行没改：`util/parse/session.py` 里的 `ParseSession` 跑的就是桌面版那套
parser 与 episode 组装，结果同样从 `signal_bus.parse.update_parse_list` 出来。
这一层只做三件事：丢出事件循环、把树转成 JSON、把异常翻成 HTTP 状态码。

## 为什么要限制并发

`ParseSession` 内部有一把锁（signal_bus 是全局的，两个解析会互相截获结果），
所以这里的请求天然是排队的。**但排队不等于可以无限排** —— 一个大 UP 主的空间要解析
几十秒，前端多点几下就能堆起一串谁也不知道还在不在的请求。这里给一个显式的上限，
超了直接回 429，比让它们默默排到超时强。
"""

from typing import Optional
import asyncio
import logging

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from util.common.config import config
from util.parse.search_url import build_search_url
from util.parse.session import ParseSession, collect_episodes
from util.thread import background

from ..schemas import EpisodeList, HistoryDeleteResult, HistoryList

logger = logging.getLogger(__name__)

router = APIRouter(tags = ["parse"])

# 同时最多排几个解析请求。解析本身是串行的，这里限制的是排队长度
MAX_PENDING_PARSES = 4

_pending = asyncio.Semaphore(MAX_PENDING_PARSES)

class ParseRequest(BaseModel):
    url: str = Field(min_length = 1, max_length = 2048)
    # 分页：个人空间、收藏夹这类按页取
    pn: int = Field(default = 1, ge = 1, le = 10000)
    # 服务端搜索的关键词。**只对接口本身支持搜索的类型有效**（个人空间、收藏夹、
    # 历史记录、稍后再看），其余类型 `build_search_url` 会原样返回链接。
    #
    # 关键词写回链接而不是另开一个参数，是桌面版定下的做法：翻页、自动解析分页、
    # 解析历史都直接复用这条链接，不必再维护一份「当前搜索状态」
    keyword: Optional[str] = Field(default = None, max_length = 200)

def _record_history(result: dict, url: str):
    """
    记一笔解析历史

    与桌面版 `on_update_parse_list` 同一个判断：开关关着就不记。
    这里是在解析线程里就地写的 —— 解析本身已经在事件循环外，再开一个线程不划算，
    而这条 INSERT 是毫秒级的
    """
    if not config.get(config.parse_history):
        return

    try:
        from util.misc.history import history_manager

        history_manager.add_history(result.get("title") or url,
                                    url, result.get("category") or "")

    except Exception as e:
        # 历史记录是附带功能，写不进去不该让整次解析失败
        logger.warning("写入解析历史失败：%s", e)

def _parse_blocking(session: ParseSession, url: str, pn: int) -> dict:
    """在工作线程里跑完解析并记一笔历史"""
    result = session.parse(url, pn)

    _record_history(result, url)

    return result

@router.post("/parse")
async def parse_url(payload: ParseRequest):
    """
    解析一个链接，返回剧集树

    树的叶子节点带 `episode` 字段 —— 那正是创建下载任务时要交回来的东西，
    前端原样回传即可，不必自己拼
    """
    if _pending.locked():
        return JSONResponse(
            {"detail": "Too many parse requests in flight",
             "code": "PARSE_BUSY"}, status_code = 429)

    async with _pending:
        session = ParseSession()

        # 关键词写回链接。不支持搜索的类型这里是个空操作
        url = build_search_url(payload.url, payload.keyword) \
            if payload.keyword is not None else payload.url

        try:
            return await asyncio.wrap_future(
                background.submit(_parse_blocking, session, url, payload.pn))

        except ValueError as e:
            # 认不出的链接 —— 用户输入的问题
            return JSONResponse({"detail": str(e)}, status_code = 400)

        except Exception as e:
            logger.warning("解析失败：%s（%s）", payload.url, e)

            return JSONResponse({"detail": str(e)}, status_code = 502)

@router.post("/parse/episodes", response_model = EpisodeList)
async def extract_episodes(tree: dict, only_checked: bool = Query(default = True)):
    """
    从解析树里把叶子摘出来

    前端完全可以自己遍历，这里提供一份是为了**让摘取规则只有一处**：
    树节点（`is_node`）不算下载项，这条规则改了两边就会对不上
    """
    return {"episodes": collect_episodes(tree, only_checked = only_checked)}

# ---------------- 解析历史 ----------------
#
# 桌面版把它存在 `history.db` 里（`util/misc/history.py`，不依赖 Qt），两端共用同一个库。
# 记录点在解析成功之后，由 `parse_history` 这个开关控住 —— 与桌面版一致。

@router.get("/parse/history", response_model = HistoryList)
async def read_history():
    from util.misc.history import history_manager

    rows = await asyncio.wrap_future(background.submit(history_manager.get_history))

    return {
        "entries": [
            {
                "history_id": row[0],
                "title": row[1] or "",
                "url": row[2] or "",
                "type": row[3] or "",
                "created_time": row[4] or 0,
            }
            for row in rows or []
        ],
        "max_length": history_manager.db_manager.max_length,
    }

@router.delete("/parse/history/{history_id}", response_model = HistoryDeleteResult)
async def delete_history(history_id: str):
    from util.misc.history import history_manager

    await asyncio.wrap_future(background.submit(history_manager.delete_history, history_id))

    # 删不存在的 id 不报错：前端可能拿的是别处已经删掉的那份列表，
    # 结果都是「这条没了」，没必要为此区分出一个错误
    return {"deleted": 1}

@router.delete("/parse/history", response_model = HistoryDeleteResult)
async def clear_history():
    from util.misc.history import history_manager

    rows = await asyncio.wrap_future(background.submit(history_manager.get_history))

    await asyncio.wrap_future(background.submit(history_manager.clear_history))

    return {"deleted": len(rows or [])}
