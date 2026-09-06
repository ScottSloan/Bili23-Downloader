"""
CDN 择优与 aria2 下载参数构造（S3-5）

D4 划的边界：aria2 只负责搬字节，**挑哪个 CDN 是业务层的事**。

最容易被误解的一点：aria2 的多 URI 不是「备选链接」，是「同一个文件并行分片到不同源」。
把候选列表整个丢给它，等于让那些本来就不通的替换节点也分到分片，反而更慢更容易失败 ——
语义不同，替代不了择优。所以这里探测出**一条**最优链接再交给 aria2。

## 为什么直接复用 GUI 那条链路

S3-5 的验收标准是「与 GUI 下载同一视频得到相同 CDN 选择」。做到这一点最可靠的方式
不是照着实现一遍，而是**调用同一个对象**：`download/parse/query_worker.py` 的
`QueryWorker`，它背后是 `network/download_url.resolve_download_url`
（分层预算、并发探测、失败节点剔除、HostHealth 冷却共享）。

两边走同一份代码，「选择一致」就是构造上成立的，不依赖两处实现不跑偏。
这条链路已经不依赖 Qt，WebUI 进程可直接用。

## 必须丢到线程里

`resolve_download_url` 是同步阻塞的，整体预算 30 秒。直接在协程里调用会把事件循环
占死那么久 —— 期间 aria2 的通知、WebSocket 推送、HTTP 请求全部停摆，且没有任何报错。

这里走 `thread/background.py` 的池（4 个线程）而不是 `asyncio.to_thread`：
后者用的默认执行器有几十个线程，批量下载时会同时打出几十份探测；探测本身内部
还会再开 8 个线程，放大之后很容易把连接池挤爆。

## 请求头

B 站的 CDN 校验 Referer 与 UA，大会员画质的流还要带 Cookie。自建下载器是把这些挂在
httpx.Client 上，aria2 这边只能靠 `--header`（RPC 里可重复出现的选项都接受数组）。

**Cookie 走 header 而不是 `--load-cookies`**：后者要往磁盘落一个 Netscape 格式的
cookie 文件，SESSDATA 是长期凭证，多一份明文落盘就多一个泄露面。
"""

from pathlib import Path
from typing import List, Optional, Union
import asyncio
import logging

from util.common.config import config
from util.download.parse.query_worker import QueryWorker
from util.download.task.info import TaskInfo
from util.network.request import get_cookies
from util.thread import background

logger = logging.getLogger(__name__)

# 下载侧的最小可用文件大小，与 GUI 的 QueryWorker.get_file_size 一致。
# 预览侧用的是 10240，那是另一条链路，不要混用
MIN_FILE_SIZE = 1024

DEFAULT_REFERER = "https://www.bilibili.com/"

# ---------------- 候选链接与探测 ----------------

def extract_urls(media_info: dict) -> List[str]:
    """
    取出全部候选链接

    刻意走 QueryWorker 的方法，好让字段名清单（baseUrl / base_url / backupUrl / ...）
    只存在一份 —— 接口哪天多一个字段，两端一起变
    """
    return QueryWorker(media_info).get_download_urls(media_info)

def resolve_dash_sync(media_info: dict) -> dict:
    """dash 单流择优，返回 {"url": ..., "file_size": ...}。失败抛 RuntimeError"""
    return QueryWorker(media_info).query_dash_url()

def resolve_mp4_sync(media_info: dict) -> List[dict]:
    """mp4 / flv 的分段择优，逐段返回 {"url", "file_size", "index"}"""
    return QueryWorker(media_info).query_mp4_url()

async def _in_background(func, *args):
    # background.submit 给的是 concurrent.futures.Future，wrap_future 把它接到事件循环上。
    # 探测里抛出的异常会原样传出来，调用方照常 try / except
    return await asyncio.wrap_future(background.submit(func, *args))

async def resolve_dash(media_info: dict) -> dict:
    return await _in_background(resolve_dash_sync, media_info)

async def resolve_mp4(media_info: dict) -> List[dict]:
    return await _in_background(resolve_mp4_sync, media_info)

# ---------------- 请求头 ----------------

def _sanitize(value) -> str:
    """
    头部值里混进 CR / LF 就是一次头注入

    Referer 取自接口返回的页面地址，UA 取自用户可编辑的配置项，两者都不该无条件信任。
    aria2 拿到的是一整行文本，坏值不会报错，只会静默多出几个头
    """
    return str(value).replace("\r", "").replace("\n", "").strip()

def format_cookie() -> str:
    """把 get_cookies() 拼成一行 Cookie 头。空值直接跳过，别送出 `key=` 这种半截项"""
    parts = []

    for key, value in get_cookies().items():
        text = _sanitize(value)

        if not text or text == "None":
            continue

        parts.append("{key}={value}".format(key = key, value = text))

    return "; ".join(parts)

def build_headers(referer: str = None, with_cookie: bool = True) -> List[str]:
    """构造 aria2 的 --header 列表。每一项是完整的一行 `Name: value`"""
    headers = [
        "Referer: {value}".format(value = _sanitize(referer or DEFAULT_REFERER)),
        "User-Agent: {value}".format(value = _sanitize(config.get(config.user_agent))),
    ]

    if with_cookie:
        cookie = format_cookie()

        if cookie:
            headers.append("Cookie: {value}".format(value = cookie))

    return headers

# ---------------- aria2 参数 ----------------

def build_options(directory: Union[str, Path], file_name: str, referer: str = None,
                  with_cookie: bool = True, extra: dict = None) -> dict:
    """
    构造 addUri 的 options

    连接数沿用 `download_thread`：用户在设置里调的是「同时下载线程数」，
    换成 aria2 之后这个数字的含义变成「对单个源开几条连接」，语义最接近
    """
    threads = config.get(config.download_thread)

    options = {
        "dir": str(directory),
        # 文件名由业务层定死（D4）。aria2 只按 --out 写
        "out": file_name,

        "header": build_headers(referer, with_cookie = with_cookie),

        # 续传交给 aria2（D4 里废弃了自建的 chunk offset 断点）
        "continue": "true",

        "max-connection-per-server": str(threads),
        "split": str(threads),
        # 分片下限。切太碎对 CDN 而言只是更多次握手，不会更快
        "min-split-size": "1M",

        # **两个都要给**：业务层已经做过文件名冲突处理，aria2 再自作主张改成
        # `xxx.1` 会让后面的合并阶段找不到文件，且不报错 —— 表现为「下载成功但合并失败」
        "allow-overwrite": "true",
        "auto-file-renaming": "false",
    }

    if extra:
        options.update(extra)

    return options

def build_global_options() -> dict:
    """
    全局限速（D4：限速改用 --max-overall-download-limit）

    配置里存的是 MB/s 的浮点数，aria2 只认整数加单位后缀，所以直接换算成字节数下发
    """
    if not config.get(config.speed_limit_enabled):
        # 关掉限速要显式下发 0，否则上一次设的值会一直留在 aria2 里
        return {"max-overall-download-limit": "0"}

    rate = config.get(config.speed_limit_rate)

    return {"max-overall-download-limit": str(int(rate * 1024 * 1024))}

# ---------------- 落库的 gid 映射 ----------------

# gid ↔ 任务的映射**必须落库**，否则后端一重启就全丢了：aria2 可能还在好好地下着，
# 而我们已经认不出哪个 gid 属于哪个任务。放在 `Download.files[file_key]` 下的独立子键里，
# 与桌面版自建下载器的分片记账（chunks_list / chunk_offsets 等）互不干扰
ARIA2_KEY = "aria2"

def remember_stream(task_info: TaskInfo, file_key: str, **fields) -> dict:
    """把一路流的 aria2 信息记进 TaskInfo（调用方负责落库）"""
    entry = task_info.Download.files.setdefault(file_key, {})

    record = entry.setdefault(ARIA2_KEY, {})

    for key, value in fields.items():
        if value is not None:
            record[key] = value

    return record

def stream_record(task_info: TaskInfo, file_key: str) -> dict:
    entry = task_info.Download.files.get(file_key)

    if not isinstance(entry, dict):
        return {}

    record = entry.get(ARIA2_KEY)

    return record if isinstance(record, dict) else {}

def stream_keys(task_info: TaskInfo) -> List[str]:
    """这个任务有哪几路流。以 files 的键为准 —— Download.queue 会随下载完成被消费掉"""
    return [key for key, entry in task_info.Download.files.items()
            if isinstance(entry, dict) and isinstance(entry.get(ARIA2_KEY), dict)]

# ---------------- 交给 aria2 ----------------

async def submit_stream(client, registry, task_id: str, file_key: str, url: str,
                        directory: Union[str, Path], file_name: str,
                        referer: str = None, with_cookie: bool = True,
                        extra: dict = None, task_info: TaskInfo = None) -> str:
    """
    把一条已经择优过的链接交给 aria2，并登记到 StreamRegistry

    先 addUri 拿到 gid 再登记：反过来的话，gid 还没拿到就登记不了，
    而 aria2 的 onDownloadStart 可能在 addUri 返回前就推过来了 ——
    那时 registry 里查不到这个 gid，事件被当成「别人的任务」丢掉，
    界面上表现为任务一直停在等待中

    传了 task_info 就顺带把 gid / url / 落盘位置记进去，供重启对账用（S3-8）
    """
    options = build_options(directory, file_name, referer = referer,
                            with_cookie = with_cookie, extra = extra)

    gid = await client.add_uri([url], options)

    registry.register(task_id, file_key, gid)

    if task_info is not None:
        remember_stream(task_info, file_key, gid = gid, url = url,
                        dir = str(directory), out = file_name, referer = referer)

    logger.info("任务 %s 的 %s 流已交给 aria2：gid=%s，文件=%s", task_id, file_key, gid, file_name)

    return gid
