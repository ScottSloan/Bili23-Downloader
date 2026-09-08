"""
检查新版本 —— 不依赖 Qt 的那一半

`update.py` 里的 `Updater` 是 QObject，走 `NetworkRequestWorker` 与 signal_bus，
那属于桌面侧。WebUI 后端跑在 asyncio 循环里，用不了它。

而**「问服务端有没有新版本」这件事本身与界面无关**：拼一个请求、读一份响应、
判断要不要更新。这里把这部分搬出来，两端共用 —— 否则 URL、请求体形状、
错误响应的判别方式会各写一遍，服务端改了协议只有一边跟得上。

`update.py` 改为从这里导入，行为一行没变。
"""

from typing import Optional, Tuple
import logging
import sys

logger = logging.getLogger(__name__)

VERHUB_BASE_URL = "https://verhub.hanloth.cn/api/v1"
VERHUB_PROJECT_KEY = "scottsloan-bili23-downloader"

CHECK_UPDATE_URL = f"{VERHUB_BASE_URL}/public/{VERHUB_PROJECT_KEY}/versions/check-update"

# 客户端来源声明，仅供服务端统计使用，不影响接口返回内容
PLATFORM_HEADER = "x-verhub-platform"
PLATFORM_VERSION_HEADER = "x-verhub-platform-version"

# 系统版本明细的长度上限，与服务端一致，超出直接截断
MAX_PLATFORM_VERSION_LENGTH = 32

# 老 Windows 的 NT 内核号 → 市场版本号，Win10 / Win11 均为 10.0，另按构建号区分
WINDOWS_NT_TO_MARKET = {
    (6, 1): "7",
    (6, 2): "8",
    (6, 3): "8.1"
}

def get_platform() -> str:
    # 只区分服务端契约中的取值，认不出时返回 others
    if sys.platform.startswith("win"):
        return "windows"

    if sys.platform == "darwin":
        return "macos"

    if sys.platform.startswith("linux"):
        return "linux"

    return "others"

def get_platform_version() -> str:
    # 版本探测纯属锦上添花，取不到就返回空串，交给服务端从 User-Agent 兜底推断
    try:
        if sys.platform.startswith("win"):
            info = sys.getwindowsversion()

            # Win11 仍上报内核 10.0，只有构建号 >= 22000 能区分出来
            if info.major == 10 and info.minor == 0:
                return "11" if info.build >= 22000 else "10"

            return WINDOWS_NT_TO_MARKET.get((info.major, info.minor), "")

        if sys.platform == "darwin":
            import platform

            return platform.mac_ver()[0]

        if sys.platform.startswith("linux"):
            import platform

            data = platform.freedesktop_os_release()

            return f"{(data.get('ID') or '').strip().lower()} {(data.get('VERSION_ID') or '').strip()}"

    except Exception:
        return ""

    return ""

def sanitize_platform_version(value: str) -> str:
    # 请求头只能承载 ASCII，非可打印字符一律当作空白处理，折叠连续空白后截断，
    # 避免编码请求头时抛出异常
    ascii_only = "".join(char if " " < char <= "~" else " " for char in value)

    return " ".join(ascii_only.split())[:MAX_PLATFORM_VERSION_LENGTH].rstrip()

def build_headers() -> dict:
    from ..common.config import config

    headers = {
        "User-Agent": f"Bili23-Downloader/{config.app_version}",
        PLATFORM_HEADER: get_platform()
    }

    # 取不到系统版本明细时不发这个头
    if platform_version := sanitize_platform_version(get_platform_version()):
        headers[PLATFORM_VERSION_HEADER] = platform_version

    return headers

def build_payload(include_preview: bool) -> dict:
    from ..common.config import config

    return {
        "current_version": config.app_version,
        "current_comparable_version": config.app_comparable_version,
        "include_preview": include_preview
    }

def get_error_message(response) -> Optional[str]:
    """
    响应是不是一条错误

    服务端返回非 2xx 时响应体形如 `{"statusCode": 400, "message": "..."}`。
    正常的响应一定带 `should_update`，拿它当判据比看状态码可靠 ——
    请求那一层是 `raise_for_status = False`，状态码不会浮上来
    """
    from ..common.translator import Translator

    if isinstance(response, dict) and "should_update" in response:
        return None

    message = response.get("message") if isinstance(response, dict) else None

    # 校验失败时 message 为字符串数组
    if isinstance(message, list):
        return "；".join(str(item) for item in message)

    return str(message) if message else Translator.ERROR_MESSAGES("UNKNOWN_ERROR")

def parse_response(response: dict) -> dict:
    """把服务端的响应摊成界面要用的那几个字段"""
    latest = response["latest_version"]

    return {
        "should_update": bool(response["should_update"]),
        "required": bool(response["required"]),
        "version": latest["version"],
        "content": latest["content"],
        "update_url": latest["download_url"],
    }

def check_for_update(include_preview: bool = False) -> Tuple[Optional[dict], Optional[str]]:
    """
    阻塞地问一次服务端。返回 (结果, 出错说明)，两者必有其一为 None

    给 WebUI 后端用 —— 桌面版走的是 `Updater` 那条 Qt 异步路径，
    两边共用的是上面那些拼请求与读响应的函数
    """
    from ..network.request import RequestType, SyncNetWorkRequest

    try:
        request = SyncNetWorkRequest(
            url = CHECK_UPDATE_URL,
            request_type = RequestType.POST,
            json_data = build_payload(include_preview),
            raise_for_status = False,
            content_type = "application/json",
            extra_headers = build_headers()
        )

        response = request.run()

    except Exception as e:
        logger.warning("检查更新失败：%s", e)

        return None, str(e)

    if error_message := get_error_message(response):
        logger.warning("检查更新失败：%s", error_message)

        return None, error_message

    return parse_response(response), None
