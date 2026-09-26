from .request import get_ssl_context, get_proxy_mounts
from .cdn import CDN, HostHealth

from ..common.config import config

from threading import Lock
import logging
import time

# 同 request.py：本模块会被解析预览链路间接引入，httpx、concurrent.futures 改为在函数内导入，
# 避免拖慢启动

logger = logging.getLogger(__name__)

PROBE_CONCURRENCY = 4                # 同时在途的探测请求数
PROBE_TIMEOUT = 5                    # 单次请求的连接 / 读写 / 等连接超时

# 刻意不设整体时间预算。任何按墙钟截断候选列表的做法，都会把"还剩候选没试"和"节点确实全坏"
# 变成同一个结果，而前者对本机网络状况毫无信息量 —— 用户看到的只是一次失败，
# 重试一次还会沿同一条时间线再失败一次（ParseWorker 的重试间隔只有 3 秒）。
#
# 总耗时改由结构决定，不再需要一个会误伤的兜底常量：
#   · 同一节点只真正发一次请求，其余同节点候选是零成本的跳过（见 failed_hosts）
#   · 单个候选至多两次请求（HEAD 取不到大小时补一次 Range GET），各自受 PROBE_TIMEOUT 约束
#   · 滑动窗口最多 PROBE_CONCURRENCY 个在途请求，波数 = 不同节点数 / PROBE_CONCURRENCY
# 按默认的 8 个节点估算，最坏（每个节点都连得上但不回包，撞满读超时）也只要两三波

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
    #    单次请求就是 4 × 5s 连接超时 + 3.5s 退避 ≈ 23s。探测的语义是"这个节点不行就立刻换
    #    下一个"，在同一个节点上反复重试纯属浪费——候选之间本来就是等价的。
    #    （http(s) 代理下 httpx 并不会把 retries 传给 httpcore.HTTPProxy，实际仍是 0 次；
    #    显式写 0 是为了直连那条路径，见 request.py 的 get_mounts 与 get_env_mounts）
    # 2. 全局 client 的连接池与解析、封面加载共用，且 pool 超时放宽到了 30s，
    #    高并发下探测请求可能光排队就耗掉很久。
    #
    # 这里单开一个 retries = 0、各项超时都收紧的 client：探测失败立刻换下一个候选，
    # 覆盖率由"扫完全部候选"保证。CDN 链接的鉴权信息全在查询参数里，不需要带 Cookie，
    # 因此也不必掺和全局 cookiejar 的跨线程读写
    global _probe_client

    if _probe_client is None:
        with _probe_client_lock:
            if _probe_client is None:
                import httpx

                ssl_context = get_ssl_context()

                _probe_client = httpx.Client(
                    # limits 必须写在 transport 上：Client 一旦收到显式 transport，就会直接拿它
                    # 当默认 transport、把自己那份 limits 整个忽略（见 request.py 的同款注释），
                    # 写在 Client 上等于没写
                    #
                    # 连接数放宽：批量下载时多个任务会同时探测（每个任务并发 PROBE_CONCURRENCY 条），
                    # 上限太低会让请求卡在连接池排队上，白白把候选判成 PoolTimeout
                    transport = httpx.HTTPTransport(
                        retries = 0,
                        limits = httpx.Limits(max_connections = 64, max_keepalive_connections = 16),
                        verify = ssl_context
                    ),
                    timeout = httpx.Timeout(PROBE_TIMEOUT, pool = PROBE_TIMEOUT),
                    # 代理模式改动需要重启程序生效，因此这里创建一次即可。
                    # 注意走代理时实际生效的是挂载里的 transport，它带的是 request.py 的
                    # 48 / 24，这里的 64 / 16 只作用于直连
                    mounts = get_proxy_mounts(),
                    follow_redirects = True,
                    verify = ssl_context
                )

    return _probe_client


def resolve_download_url(url_list: list[str], min_file_size: int = 1024) -> dict:
    from concurrent.futures import ThreadPoolExecutor

    start = time.monotonic()

    candidate_list = CDN.get_candidate_urls(url_list)

    if not candidate_list:
        raise RuntimeError("无法获取有效的下载链接（接口未返回任何链接）")

    # 本次解析中已经失败过的节点。同一个节点换一条链接去请求结果也一样，
    # 直接跳过，把并发位留给还没试过的节点
    failed_hosts = set()
    stats = {
        "attempted": 0,
        "skipped": 0,
        "reasons": [],
        "inconclusive": []
    }

    # 每次调用单独建一个小线程池：批量下载时会有多个任务同时解析，
    # 共用一个固定大小的线程池反而会让各任务互相排队，把等待时间算进彼此的耗时里。
    #
    # 线程数与并发数相等即可：滑动窗口只在有空闲线程时才提交下一个候选，
    # 不存在"被放弃却还占着线程"的请求
    executor = ThreadPoolExecutor(max_workers = PROBE_CONCURRENCY, thread_name_prefix = "cdn-probe")

    try:
        result = _probe_candidates(executor, candidate_list, min_file_size, failed_hosts, stats)

        if result is None and stats["inconclusive"]:
            # 唯一值得补测的是"没能得出结论"的候选（连接池排队）：它既不能算节点失败
            # （与本机并发状况有关，与节点好坏无关），也不该被就此丢掉 —— 批量下载时几十个任务
            # 共用同一个探测 client，第一轮撞上排队是常态；此时其它任务多半已经结束、
            # 连接池腾空，补一遍往往就能拿到结论。
            # 只在第一轮全军覆没后才会走这一步，命中候选的正常路径上零成本
            retry_list = stats["inconclusive"]
            stats["inconclusive"] = []

            result = _probe_candidates(executor, retry_list, min_file_size, failed_hosts, stats)

        if result:
            return result

    finally:
        # 不等待仍在途的探测请求：它们各自有 5s 硬超时，让其自然结束即可，
        # 否则一个慢节点会把整个解析流程拖住
        executor.shutdown(wait = False, cancel_futures = True)

    host_count = len({CDN.get_netloc(url) for url in candidate_list})

    logger.warning(
        "全部候选链接探测失败，候选 %s 个（%s 个节点），实际探测 %s 个，同节点跳过 %s 个，耗时 %.1f 秒，失败原因：%s",
        len(candidate_list), host_count, stats["attempted"], stats["skipped"],
        time.monotonic() - start, "，".join(stats["reasons"][:8]) or "无"
    )

    # 按节点口径报数：候选是按"节点 × 备份链接数"展开的，同一节点上换一条链接结果一样，
    # 所以真正的探测单位是节点数而不是候选数。原先那句"共 24 个候选，已尝试 12 个"把
    # 同节点跳过也算进了差额里，读起来像是程序只试了一半就放弃
    raise RuntimeError("无法获取有效的下载链接（{total} 个候选覆盖 {hosts} 个 CDN 节点，均已探测失败）".format(
        total = len(candidate_list),
        hosts = host_count
    ))


def _probe_candidates(executor, candidate_list: list[str], min_file_size: int, failed_hosts: set, stats: dict) -> dict:
    from concurrent.futures import wait, FIRST_COMPLETED

    pending = {}
    order = {}
    index = 0
    count = len(candidate_list)

    def fill():
        # 滑动窗口：每有一个候选出结果就补进下一个，而不是整批等齐再发下一批。
        # 整批等待会把一批里最慢的那个节点的耗时累加到每一轮上，候选一多就慢得离谱
        nonlocal index

        while len(pending) < PROBE_CONCURRENCY and index < count:
            url = candidate_list[index]
            position = index
            index += 1

            if CDN.get_netloc(url) in failed_hosts:
                stats["skipped"] += 1
                continue

            future = executor.submit(_probe_url, url, min_file_size)

            pending[future] = url
            # 记下候选在列表里的位置。同一批里可能有多个候选同时成功，而 done 是个 set、
            # 遍历顺序不确定，返回哪一个必须由候选顺序决定 —— 扁平化之后，
            # "首选层排在前"这份用户偏好全靠顺序承载
            order[future] = position

    fill()

    # pending 为空就退出，不留空转的可能：wait 至少要有一个 future 才调用
    while pending:
        done, _ = wait(list(pending), return_when = FIRST_COMPLETED)

        winners = []

        for future in done:
            url = pending.pop(future)
            host = CDN.get_netloc(url)

            try:
                file_size, reason = future.result()

            except Exception as e:
                file_size, reason = 0, type(e).__name__

            stats["attempted"] += 1

            if file_size > min_file_size:
                winners.append((order[future], url, file_size))
                continue

            stats["reasons"].append("{host} {reason}".format(host = host, reason = reason))

            if reason in INCONCLUSIVE_REASONS:
                # 没得出结论：不能记为节点故障，也不能就此丢弃，留给第二轮补测
                stats["inconclusive"].append(url)
                continue

            failed_hosts.add(host)
            HostHealth.report_failure(host)

        if winners:
            _, url, file_size = min(winners)
            HostHealth.report_success(CDN.get_netloc(url))

            return {
                "url": url,
                "file_size": file_size
            }

        fill()

    return None


def _probe_url(url: str, min_file_size: int) -> tuple[int, str]:
    # 这里不再对同一个候选做重试：候选之间本就是等价的，与其反复请求同一个节点，
    # 不如把这一次时间花在下一个还没试过的节点上。真正的瞬时故障由任务级重试兜底，见 ParseWorker
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
