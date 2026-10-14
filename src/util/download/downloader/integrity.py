"""
下载数据的完整性校验（Issue #449）

分片完成的判据只能保证「每一片都写满了」，保证不了「写进去的是对的字节」。
用户提供的对比结果里，损坏区域无一例外是从某个分片中间的续传点一直坏到分片末尾，
或者整片都坏 —— 这正是服务端对 Range 请求回了 206、但给的不是所请求那一段时的样子。
程序原先不看 Content-Range，照单全收，坏数据就这样一路进了 FFmpeg，
表现为花屏、重新封装丢数据、音画不同步。

这里提供两道校验：

1. 逐个响应核对 Content-Range 与 ETag，确认节点给的确实是所请求文件的所请求区间
2. 文件下载完成后与 ETag 比对 MD5。upos 系节点的 ETag 就是整个文件的 MD5
   （各镜像一致，华为节点还会同时给出等值的 Content-MD5），PCDN 节点不返回 ETag，
   这道校验只在拿得到时生效
"""

from threading import Event
from pathlib import Path
import hashlib
import re

_CONTENT_RANGE_PATTERN = re.compile(r"^\s*bytes\s+(\d+)-(\d+)/(\d+|\*)\s*$", re.IGNORECASE)
_MD5_PATTERN = re.compile(r"^[0-9a-f]{32}$")

class ResponseMismatchError(Exception):
    """节点返回的数据与请求不符。此时一个字节都不能写入，换个时机或换个节点重来"""
    pass

def parse_content_range(value: str | None):
    """
    解析 `bytes start-end/total`，返回 (start, end, total)，total 未知时为 None

    格式不合法时返回 None。end 按 HTTP 语义是闭区间
    """
    if not value:
        return None

    match = _CONTENT_RANGE_PATTERN.match(value)

    if not match:
        return None

    start, end, total = match.groups()

    return int(start), int(end), None if total == "*" else int(total)

def normalize_etag(value: str | None) -> str:
    # 各镜像返回的大小写不一（阿里云是大写，其余是小写），弱校验前缀与引号同样去掉
    if not value:
        return ""

    value = value.strip()

    if value[:2].upper() == "W/":
        value = value[2:]

    return value.strip('"').lower()

def is_md5(etag: str) -> bool:
    # 只有形如 MD5 的 ETag 才能拿来比对内容。nginx 那种「修改时间-长度」的 ETag
    # 换个节点就变，拿来判定会把正常节点误判成坏节点
    return bool(_MD5_PATTERN.match(etag or ""))

def file_md5(path: Path, stop_event: Event = None, block_size: int = 4 * 1024 * 1024):
    """计算文件 MD5，中途被叫停时返回 None"""
    digest = hashlib.md5()

    with open(path, "rb") as f:
        while True:
            if stop_event is not None and stop_event.is_set():
                return None

            block = f.read(block_size)

            if not block:
                break

            digest.update(block)

    return digest.hexdigest()
