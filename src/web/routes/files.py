"""
文件系统浏览（S3-10）

给前端选下载目录用。**只读，且只在白名单根目录内**（新建目录是唯一的写操作）。

安全部分全在 `web/paths.py`，这里只负责别绕过它：**任何接触文件系统的调用都必须用
`resolve_within_roots()` 的返回值**，拿请求里的原始字符串去开目录等于白检查一遍。

不提供的东西也是有意的：不读文件内容、不删文件、不重命名。
浏览接口存在的理由只是「让用户挑一个目录」，多一个能力就多一份被利用的可能。
"""

from pathlib import Path
from typing import Optional
import logging
import os

from fastapi import APIRouter, Query
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from ..paths import PathNotAllowed, browse_roots, relative_label, resolve_within_roots

from ..schemas import DirectoryListing, FileRoots, MakeDirResult

logger = logging.getLogger(__name__)

router = APIRouter(tags = ["files"])

# 单次返回的条目上限。某些目录（下载目录本身）可能有上万个文件，
# 一次全塞给前端既慢又没用
MAX_ENTRIES = 2000

class MkdirRequest(BaseModel):
    path: str = Field(min_length = 1, max_length = 4096)
    name: str = Field(min_length = 1, max_length = 255)

def _denied(exc: PathNotAllowed) -> JSONResponse:
    # 403 而不是 404：路径不合法是权限问题。也不要把解析后的真实路径回给前端 ——
    # 那等于把「这个路径存在吗」变成一个可探测的接口
    return JSONResponse({"detail": str(exc)}, status_code = 403)

@router.get("/files/roots", response_model = FileRoots)
async def list_roots():
    """可浏览的根目录。前端据此显示入口，不给用户输入任意路径的机会"""
    roots = browse_roots()

    return {
        "roots": [
            {"path": str(root), "name": root.name or str(root), "exists": root.is_dir()}
            for root in roots
        ]
    }

@router.get("/files/list", response_model = DirectoryListing)
async def list_directory(path: str = Query(default = ""),
                         dirs_only: bool = Query(default = False)):
    """列出一个目录。`path` 为空时给第一个根目录"""
    roots = browse_roots()

    try:
        target = resolve_within_roots(path, roots)

    except PathNotAllowed as e:
        return _denied(e)

    if not target.is_dir():
        return JSONResponse({"detail": "Not a directory"}, status_code = 404)

    entries = []
    truncated = False

    try:
        with os.scandir(target) as it:
            for entry in it:
                if len(entries) >= MAX_ENTRIES:
                    truncated = True

                    break

                try:
                    is_dir = entry.is_dir()

                except OSError:
                    # 坏掉的链接、权限不足的项。跳过比让整个列表取不出来强
                    continue

                if dirs_only and not is_dir:
                    continue

                try:
                    stat = entry.stat()

                    size = 0 if is_dir else stat.st_size
                    mtime = int(stat.st_mtime)

                except OSError:
                    size, mtime = 0, 0

                entries.append({
                    "name": entry.name,
                    "is_dir": is_dir,
                    "size": size,
                    "modified": mtime,
                    # 链接单独标出来：它可能指向根目录之外，点进去会被拒，
                    # 前端提前显示出来比让用户撞一次墙好
                    "is_link": entry.is_symlink(),
                })

    except PermissionError:
        return JSONResponse({"detail": "Permission denied"}, status_code = 403)

    except OSError as e:
        logger.warning("列目录失败：%s（%s）", target, e)

        return JSONResponse({"detail": "Cannot read directory"}, status_code = 400)

    entries.sort(key = lambda item: (not item["is_dir"], item["name"].lower()))

    parent = _parent_within(target, roots)

    return {
        "path": str(target),
        "relative": relative_label(target, roots),
        # 已经在根上时为 None，前端据此禁用「上一级」
        "parent": parent,
        "entries": entries,
        "truncated": truncated,
    }

@router.post("/files/mkdir", response_model = MakeDirResult)
async def make_directory(payload: MkdirRequest):
    """
    在允许的目录下新建一个子目录

    `name` 只能是单个名字，不能是路径：允许它带分隔符的话，`../../x` 就又回来了。
    这里既拦名字本身，也仍然让结果过一遍 `resolve_within_roots`
    """
    name = payload.name.strip()

    if not name or name in (".", ".."):
        return JSONResponse({"detail": "Invalid folder name"}, status_code = 400)

    if os.sep in name or (os.altsep and os.altsep in name) or "/" in name or "\\" in name:
        return JSONResponse({"detail": "Folder name cannot contain path separators"},
                            status_code = 400)

    roots = browse_roots()

    try:
        parent = resolve_within_roots(payload.path, roots)

        # 拼好之后再查一次：名字本身已经拦过分隔符，但符号链接之类还是要靠这一步
        target = resolve_within_roots(str(parent / name), roots)

    except PathNotAllowed as e:
        return _denied(e)

    if not parent.is_dir():
        return JSONResponse({"detail": "Parent is not a directory"}, status_code = 404)

    try:
        target.mkdir(parents = False, exist_ok = True)

    except OSError as e:
        logger.warning("新建目录失败：%s（%s）", target, e)

        return JSONResponse({"detail": "Cannot create directory"}, status_code = 400)

    return {"path": str(target), "relative": relative_label(target, roots)}

def _parent_within(target: Path, roots) -> Optional[str]:
    """上一级目录，越界则返回 None"""
    parent = target.parent

    if parent == target:
        return None

    try:
        return str(resolve_within_roots(str(parent), roots))

    except PathNotAllowed:
        return None
