"""
路径穿越防护（S3-10）

浏览接口是整个后端**唯一能读到任意路径**的地方。这一层的规则是反过来的：
不在白名单根目录里的路径一律拒绝，而不是「默认放开、按需拦」。

## 只做前缀判断是不够的

三条常见的漏法，这里都堵上，测试也逐条盯着：

1. **`..`** —— 光靠 `"../" not in path` 挡不住：URL 编码、`....//`、Windows 的 `..\\`
   都能绕过。正确做法是**规范化之后再比较**，不去检查原始字符串长什么样。
2. **符号链接 / 目录联接** —— 根目录里放一个指向 `C:\\` 的链接，字符串前缀完全合法，
   实际读到的却是外面。所以必须 `resolve()`，让链接先解开再判断。
   Windows 上的目录联接（junction）不需要管理员权限就能建，是最容易被忽略的一种。
3. **兄弟目录的前缀重合** —— 根是 `/data/downloads` 时，`/data/downloads-evil`
   以它为前缀却完全在外面。判断必须带上分隔符。

## Windows 的两处额外坑

- **大小写**。`C:\\Downloads` 与 `c:\\downloads` 是同一个目录，但字符串比较不是。
  统一走 `os.path.normcase`。
- **短文件名**（`PROGRA~1`）。`resolve()` 对**已存在**的路径会通过
  `GetFinalPathNameByHandle` 拿到长名，不存在的路径则原样保留。所以判断要基于
  「存在的那部分」—— 下面 `_resolve_existing()` 逐级往上找到第一个存在的祖先再解析。
"""

from pathlib import Path
from typing import List, Optional
import logging
import os

from util.common.config import config

logger = logging.getLogger(__name__)

class PathNotAllowed(Exception):
    """目标路径不在任何一个白名单根目录内"""

def _normcase(path: Path) -> str:
    # Windows 上大小写不敏感，Linux / macOS 上 normcase 是恒等变换
    return os.path.normcase(str(path))

def _resolve_existing(path: Path) -> Path:
    """
    解析出真实路径，对还不存在的部分保持原样

    直接 `path.resolve()` 也能用，但对不存在的路径它只做纯字符串规范化，
    Windows 上短文件名不会被展开。这里先找到第一个存在的祖先并解析它 ——
    符号链接与联接都在那一段上，展开之后再把剩下的相对部分接回去
    """
    path = Path(path)

    try:
        if path.exists():
            return path.resolve()

    except OSError:
        # 路径太长、含非法字符、或指向一个坏掉的链接
        pass

    parts: List[str] = []
    current = path

    while True:
        parent = current.parent

        if parent == current:
            # 到根了，整条路径都不存在
            break

        parts.append(current.name)

        current = parent

        try:
            if current.exists():
                break

        except OSError:
            break

    try:
        base = current.resolve()

    except OSError:
        base = current

    for name in reversed(parts):
        base = base / name

    return base

def is_within(root: Path, target: Path) -> bool:
    """
    target 是否在 root 之内（含 root 自身）

    两边都必须是**已经解析过**的路径，这个函数不负责解析
    """
    root_key = _normcase(root)
    target_key = _normcase(target)

    if target_key == root_key:
        return True

    # **必须带上分隔符**：根是 /data/downloads 时，/data/downloads-evil
    # 以它为前缀却完全在外面
    if not root_key.endswith(os.sep):
        root_key += os.sep

    return target_key.startswith(root_key)

def browse_roots() -> List[Path]:
    """
    白名单根目录

    配置为空时只允许下载目录本身 —— 这是最小可用的范围，也是 Docker 的常态
    （一个挂载点）。要多开就在 `webui_browse_roots` 里显式列出
    """
    roots: List[Path] = []

    configured = config.get(config.webui_browse_roots) or []

    for entry in configured:
        if not entry:
            continue

        roots.append(_resolve_existing(Path(str(entry))))

    download_path = config.get(config.download_path)

    if download_path:
        resolved = _resolve_existing(Path(download_path))

        if not any(is_within(root, resolved) for root in roots):
            roots.append(resolved)

    return roots

def resolve_within_roots(candidate: str, roots: List[Path] = None) -> Path:
    """
    把用户给的路径解析成真实路径，并确认它落在某个根目录内

    不在的话抛 `PathNotAllowed`。**调用方一律用这个函数的返回值去访问文件系统**，
    拿原始字符串去开文件等于白做一遍检查
    """
    if roots is None:
        roots = browse_roots()

    if not roots:
        raise PathNotAllowed("没有配置任何可浏览的目录")

    if not candidate:
        return roots[0]

    resolved = _resolve_existing(Path(candidate))

    for root in roots:
        if is_within(root, resolved):
            return resolved

    logger.warning("拒绝越界的路径访问：%s（解析为 %s）", candidate, resolved)

    raise PathNotAllowed("路径不在允许浏览的目录内")

def relative_label(path: Path, roots: List[Path] = None) -> Optional[str]:
    """相对于所属根目录的展示用路径。用于前端面包屑，不参与任何安全判断"""
    if roots is None:
        roots = browse_roots()

    for root in roots:
        if is_within(root, path):
            try:
                return str(path.relative_to(root))

            except ValueError:
                # 大小写不同导致 relative_to 失败（Windows）。展示用途，退回绝对路径即可
                return str(path)

    return None
