from .request import RequestType, ResponseType, SyncNetWorkRequest, get_client
from .cdn import CDN

from urllib.parse import urlparse
import logging
import time
import httpx

logger = logging.getLogger(__name__)

PROBE_ATTEMPTS = 2
PROBE_RETRY_DELAY = 0.5
PROBE_TIMEOUT = 5
PROBE_TOTAL_TIMEOUT = 30
RETRYABLE_STATUS_CODES = {408, 429, 500, 502, 503, 504}


def resolve_download_url(url_list: list[str], min_file_size: int = 1024) -> dict:
    deadline = time.monotonic() + PROBE_TOTAL_TIMEOUT

    for url in CDN.get_url_list(url_list):
        if time.monotonic() >= deadline:
            break

        file_size = _probe_url(url, min_file_size, deadline)

        if file_size > min_file_size:
            return {
                "url": url,
                "file_size": file_size
            }

    raise RuntimeError("无法获取有效的下载链接")


def _probe_url(url: str, min_file_size: int, deadline: float) -> int:
    for attempt in range(PROBE_ATTEMPTS):
        if time.monotonic() >= deadline:
            return 0

        try:
            file_size = _probe_with_head(url, min_file_size)

            if file_size > min_file_size:
                return file_size

            return 0

        except httpx.HTTPStatusError as exc:
            status_code = exc.response.status_code
            retryable = status_code in RETRYABLE_STATUS_CODES or status_code >= 500
            logger.debug("CDN probe returned HTTP %s for %s", status_code, urlparse(url).netloc)

        except httpx.RequestError as exc:
            retryable = True
            logger.debug("CDN probe request failed for %s: %s", urlparse(url).netloc, exc)

        if not retryable or attempt + 1 >= PROBE_ATTEMPTS:
            return 0

        remaining = deadline - time.monotonic()

        if remaining <= 0:
            return 0

        time.sleep(min(PROBE_RETRY_DELAY * (2 ** attempt), remaining))

    return 0


def _probe_with_head(url: str, min_file_size: int) -> int:
    request = SyncNetWorkRequest(
        url,
        request_type = RequestType.HEAD,
        response_type = ResponseType.RESPONSE,
        raise_for_status = False
    )
    response = request.run()

    if response.status_code == 405:
        return _probe_with_range_get(url)

    response.raise_for_status()
    file_size = _extract_file_size(response.headers)

    if file_size > min_file_size:
        return file_size

    return _probe_with_range_get(url)


def _probe_with_range_get(url: str) -> int:
    # 原先靠 update_headers() 改写全局 client 来带上 UA / Referer，
    # 现在直接把头部传给本次请求，不再依赖全局状态
    headers = SyncNetWorkRequest(url).get_headers()
    headers["Range"] = "bytes=0-0"

    with get_client().stream(
        "GET",
        url,
        headers = headers,
        timeout = PROBE_TIMEOUT
    ) as response:
        response.raise_for_status()

        return _extract_file_size(response.headers)


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
