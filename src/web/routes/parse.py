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

from util.parse.session import ParseSession, collect_episodes
from util.thread import background

from ..schemas import EpisodeList

logger = logging.getLogger(__name__)

router = APIRouter(tags = ["parse"])

# 同时最多排几个解析请求。解析本身是串行的，这里限制的是排队长度
MAX_PENDING_PARSES = 4

_pending = asyncio.Semaphore(MAX_PENDING_PARSES)

class ParseRequest(BaseModel):
    url: str = Field(min_length = 1, max_length = 2048)
    # 分页：个人空间、收藏夹这类按页取
    pn: int = Field(default = 1, ge = 1, le = 10000)

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

        try:
            return await asyncio.wrap_future(
                background.submit(session.parse, payload.url, payload.pn))

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
