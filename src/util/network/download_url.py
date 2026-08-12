from .request import get_ssl_context, get_proxy_mounts
from .cdn import CDN, HostHealth

from ..common.config import config

from threading import Lock
import logging
import time

# 同 request.py：本模块会被解析预览链路间接引入，httpx、concurrent.futures 改为在函数内导入，
# 避免拖慢启动

logger = logging.getLogger(__name__)

PROBE_CONCURRENCY = 4                # 单批同时探测的候选数量
PROBE_TIMEOUT = 5                    # 单次请求的连接 / 读写 / 等连接超时
PROBE_TOTAL_TIMEOUT = 30             # 整体时间预算
PROBE_PRIMARY_BUDGET_RATIO = 0.6     # 首选层最多占用的预算比例，其余强制留给兜底层

# 这类失败源于本机连接池排队，与节点本身好坏无关，不能计入节点健康状态，
# 否则批量下载时的自身并发会把好节点误判成故障节点
INCONCLUSIVE_REASONS = {
    "PoolTimeout"
}

_probe_client = None
_probe_client_lock = Lock()


def get_probe_client():
    # 探测刻意不复用 request.py 的全局 client：
    #
    # 1. 全局 client 的 transport 带 retries = 3，遇到不回包的节点 httpx 会自己连续重试 4 次，
    #    单次请求就是 4 × 5s 连接超时 + 3.5s 退避 ≈ 23s。而整体预算只有 30s，
    #    一个黑洞节点就能把预算吃光，后面的候选（包括一定可用的原始链接）全都轮不到。
    # 2. 全局 client 的连接池与解析、封面加载共用，且 pool 超时放宽到了 30s，
    #    高并发下探测请求可能光排队就耗掉整份预算。
    #
    # 这里单开一个 retries = 0、各项超时都收紧的 client：探测失败立刻换下一个候选，
    # 由并发 + 分层预算来保证覆盖率。CDN 链接的鉴权信息全在查询参数里，不需要带 Cookie，
    # 因此也不必掺和全局 cookiejar 的跨线程读写
    global _probe_client

    if _probe_client is None:
        with _probe_client_lock:
            if _probe_client is None:
                import httpx

                ssl_context = get_ssl_context()

                _probe_client = httpx.Client(
                    # 连接数放宽：批量下载时多个任务会同时探测（每个任务并发 PROBE_CONCURRENCY 条），
                    # 上限太低会让请求卡在连接池排队上，白白吃掉时间预算
                    limits = httpx.Limits(max_connections = 64, max_keepalive_connections = 16),
                    timeout = httpx.Timeout(PROBE_TIMEOUT, pool = PROBE_TIMEOUT),
                    transport = httpx.HTTPTransport(retries = 0, verify = ssl_context),
                    # 代理模式改动需要重启程序生效，因此这里创建一次即可
                    mounts = get_proxy_mounts(),
                    follow_redirects = True,
                    verify = ssl_context
                )

    return _probe_client


def resolve_download_url(url_list: list[str], min_file_size: int = 1024) -> dict:
    from concurrent.futures import ThreadPoolExecutor

    start = time.monotonic()
    deadline = start + PROBE_TOTAL_TIMEOUT

    tier_list = [tier for tier in CDN.get_url_tiers(url_list) if tier]

    if not tier_list:
        raise RuntimeError("无法获取有效的下载链接（接口未返回任何链接）")

    # 本次解析中已经失败过的节点。同一个节点换一条链接去请求结果也一样，
    # 直接跳过，把预算留给还没试过的节点
    failed_hosts = set()
    stats = {
        "attempted": 0,
        "reasons": []
    }

    # 每次调用单独建一个小线程池：批量下载时会有多个任务同时解析，
    # 共用一个固定大小的线程池反而会让各任务互相排队，把等待时间算进彼此的预算里。
    #
    # 线程数给到并发数的两倍：某一层预算耗尽时，被放弃的请求还会占着线程直到自己超时，
    # 若线程数与并发数相等，兜底层就得先等它们腾出线程，白白吃掉一段兜底预算
    executor = ThreadPoolExecutor(max_workers = PROBE_CONCURRENCY * 2, thread_name_prefix = "cdn-probe")

    try:
        for index, tier in enumerate(tier_list):
            if index < len(tier_list) - 1:
                # 首选层只能用掉一部分预算，剩下的强制留给兜底层
                tier_deadline = min(deadline, start + PROBE_TOTAL_TIMEOUT * PROBE_PRIMARY_BUDGET_RATIO)
            else:
                tier_deadline = deadline

            result = _probe_tier(executor, tier, min_file_size, tier_deadline, failed_hosts, stats)

            if result:
                return result

    finally:
        # 不等待仍在途的探测请求：它们各自有 5s 硬超时，让其自然结束即可，
        # 否则一个慢节点会把整个解析流程拖住
        executor.shutdown(wait = False, cancel_futures = True)

    total_count = sum(len(tier) for tier in tier_list)

    logger.warning(
        "全部候选链接探测失败，候选 %s 个，实际尝试 %s 个，失败原因：%s",
        total_count, stats["attempted"], "，".join(stats["reasons"][:8]) or "无"
    )

    raise RuntimeError("无法获取有效的下载链接（共 {total} 个候选，已尝试 {attempted} 个）".format(
        total = total_count,
        attempted = stats["attempted"]
    ))


def _probe_tier(executor, url_list: list[str], min_file_size: int, deadline: float, failed_hosts: set, stats: dict) -> dict:
    index = 0
    count = len(url_list)

    while index < count:
        if time.monotonic() >= deadline:
            return None

        batch = []

        while index < count and len(batch) < PROBE_CONCURRENCY:
            url = url_list[index]
            index += 1

            if CDN.get_netloc(url) in failed_hosts:
                continue

            batch.append(url)

        if not batch:
            continue

        result = _probe_batch(executor, batch, min_file_size, deadline, failed_hosts, stats)

        if result:
            return result

    return None


def _probe_batch(executor, batch: list[str], min_file_size: int, deadline: float, failed_hosts: set, stats: dict) -> dict:
    from concurrent.futures import wait, FIRST_COMPLETED

    future_map = {executor.submit(_probe_url, url, min_file_size): url for url in batch}
    pending = set(future_map)

    try:
        while pending:
            remaining = deadline - time.monotonic()

            if remaining <= 0:
                return None

            done, pending = wait(pending, timeout = remaining, return_when = FIRST_COMPLETED)

            if not done:
                # 预算用尽，仍在途的请求一并放弃。这些候选没有得出结论，
                # 因此不能记为失败，否则会误判节点健康状态
                return None

            for future in done:
                url = future_map[future]
                host = CDN.get_netloc(url)

                try:
                    file_size, reason = future.result()

                except Exception as e:
                    file_size, reason = 0, type(e).__name__

                stats["attempted"] += 1

                if file_size > min_file_size:
                    HostHealth.report_success(host)

                    return {
                        "url": url,
                        "file_size": file_size
                    }

                stats["reasons"].append("{host} {reason}".format(host = host, reason = reason))

                if reason in INCONCLUSIVE_REASONS:
                    continue

                failed_hosts.add(host)
                HostHealth.report_failure(host)

        return None

    finally:
        for future in future_map:
            future.cancel()


def _probe_url(url: str, min_file_size: int) -> tuple[int, str]:
    # 这里不再对同一个候选做重试：候选之间本就是等价的，与其反复请求同一个节点，
    # 不如把预算花在下一个节点上。真正的瞬时故障由任务级重试兜底，见 ParseWorker
    import httpx

    try:
        file_size = _probe_with_head(url, min_file_size)

        if file_size > min_file_size:
            return file_size, ""

        return 0, "文件大小无效"

    except httpx.HTTPStatusError as e:
        return 0, "HTTP {code}".format(code = e.response.status_code)

    except httpx.RequestError as e:
        return 0, type(e).__name__

    except Exception as e:
        # httpx.InvalidURL 之类不属于上面两类的异常同样不能让整轮探测中断
        return 0, type(e).__name__


def _probe_with_head(url: str, min_file_size: int) -> int:
    response = get_probe_client().head(url, headers = _get_probe_headers())

    if response.status_code == 405:
        return _probe_with_range_get(url)

    response.raise_for_status()
    file_size = _extract_file_size(response.headers)

    if file_size > min_file_size:
        return file_size

    return _probe_with_range_get(url)


def _probe_with_range_get(url: str) -> int:
    headers = _get_probe_headers()
    headers["Range"] = "bytes=0-0"

    with get_probe_client().stream("GET", url, headers = headers) as response:
        response.raise_for_status()

        return _extract_file_size(response.headers)


def _get_probe_headers() -> dict:
    return {
        "Referer": "https://www.bilibili.com/",
        "User-Agent": config.get(config.user_agent)
    }


def _extract_file_size(headers) -> int:
    content_type = headers.get("Content-Type", "").lower()

    if not content_type or "text" in content_type or "json" in content_type:
        return 0

    content_range = headers.get("Content-Range", "")
    range_total = content_range.rpartition("/")[2].strip()

    if range_total.isdigit():
        return int(range_total)

    content_length = headers.get("Content-Length", "")

    if str(content_length).isdigit():
        return int(content_length)

    return 0
