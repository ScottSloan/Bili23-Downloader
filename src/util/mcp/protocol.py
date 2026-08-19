from ..common.config import config

import logging

logger = logging.getLogger(__name__)

# 本服务器实现的协议版本。
#
# 2026-07-28 起协议做了破坏性简化：取消 initialize 握手（改为每个请求在
# params._meta 里自带版本）、移除协议级 session、移除 GET 流端点，并新增
# 强制的 server/discover。我们的工具全是请求-响应式，正好只需要
# "POST 进来、算完返回 JSON" 这一条路径。
#
# 但客户端生态未必都已跟进，因此同时保留 initialize 握手那一代（legacy）的
# 支持。规范允许同一端点同时服务两代（dual-era），且对我们成本很低：
# 差异只有握手方式、请求头校验、resultType 字段三处。
MODERN_VERSION = "2026-07-28"

LEGACY_VERSIONS = ["2025-11-25", "2025-06-18", "2025-03-26"]

SUPPORTED_VERSIONS = [MODERN_VERSION] + LEGACY_VERSIONS

PROTOCOL_VERSION_KEY = "io.modelcontextprotocol/protocolVersion"
SERVER_INFO_KEY = "io.modelcontextprotocol/serverInfo"

SERVER_INSTRUCTIONS = (
    "Controls the Bili23 Downloader desktop application. Parse a Bilibili URL first, "
    "then inspect the parsed episodes and create download tasks from them. "
    "Parsing replaces whatever is currently shown in the application's parse list, "
    "so it is refused while the user has items selected there."
)

# JSON-RPC 错误码。-32020 与 -32022 来自 MCP 规范为协议保留的区间，
# 不要自行改动取值，客户端按这些码做分支
# 缓存提示。规范要求所有 resultType 为 "complete" 的结果都必须带上 ttlMs 与
# cacheScope，缺失会被客户端判为非法结果而整个拒收（不是降级处理）。
#
# 我们声明 listChanged 为 false，不发送变更通知，客户端只能靠 TTL 感知变化：
# 工具列表会随「允许下载操作」开关增减，所以取一个较短的值，让用户改完设置后
# 很快生效；discover 的内容只随程序版本变，可以缓存久一些。
#
# cacheScope 取 public：两者都只包含工具描述与服务器信息，不含用户数据。
TOOLS_CACHE_TTL_MS = 60_000
DISCOVER_CACHE_TTL_MS = 300_000
CACHE_SCOPE = "public"

PARSE_ERROR = -32700
INVALID_REQUEST = -32600
METHOD_NOT_FOUND = -32601
INVALID_PARAMS = -32602
INTERNAL_ERROR = -32603
HEADER_MISMATCH = -32020
UNSUPPORTED_PROTOCOL_VERSION = -32022

def make_error(request_id, code: int, message: str, data = None):
    error = {"code": code, "message": message}

    if data is not None:
        error["data"] = data

    return {"jsonrpc": "2.0", "id": request_id, "error": error}

def make_result(request_id, result: dict):
    return {"jsonrpc": "2.0", "id": request_id, "result": result}

def unsupported_version_error(request_id, requested: str):
    return make_error(
        request_id,
        UNSUPPORTED_PROTOCOL_VERSION,
        "Unsupported protocol version",
        {"supported": SUPPORTED_VERSIONS, "requested": requested}
    )

def get_request_version(message: dict) -> str:
    """
    取出请求声明的协议版本

    modern 请求在 params._meta 中携带；legacy 的 initialize 放在 params.protocolVersion；
    legacy 的后续请求则不带任何版本信息（靠握手时协商的结果）
    """
    params = message.get("params") or {}

    meta = params.get("_meta") or {}

    if version := meta.get(PROTOCOL_VERSION_KEY):
        return version

    if version := params.get("protocolVersion"):
        return version

    return ""

def is_modern_request(message: dict) -> bool:
    params = message.get("params") or {}

    meta = params.get("_meta") or {}

    return bool(meta.get(PROTOCOL_VERSION_KEY))

class Dispatcher:
    """
    JSON-RPC 方法分发

    只负责协议形状，不关心 HTTP。传输层（server.py）负责鉴权、Origin 校验与
    请求头一致性校验，把解析好的消息体交到这里。
    """
    def __init__(self, tool_registry):
        self.tools = tool_registry

    def handle(self, message: dict):
        """
        处理单条 JSON-RPC 消息

        返回 (http_status, response_body)。response_body 为 None 时表示
        无需响应体（通知消息，按规范回 202）
        """
        if not isinstance(message, dict) or message.get("jsonrpc") != "2.0":
            return 400, make_error(None, INVALID_REQUEST, "Invalid JSON-RPC 2.0 message")

        method = message.get("method")

        if not isinstance(method, str):
            return 400, make_error(message.get("id"), INVALID_REQUEST, "Missing method")

        request_id = message.get("id")

        # 无 id 即为通知。规范要求接受后回 202 且不带响应体
        is_notification = "id" not in message

        version = get_request_version(message)

        # 版本校验只在请求声明了版本时进行。legacy 握手之后的请求不带版本，
        # 此时无从校验，按已协商的结果处理
        if version and version not in SUPPORTED_VERSIONS:
            if is_notification:
                return 400, None

            return 400, unsupported_version_error(request_id, version)

        modern = is_modern_request(message)

        try:
            if is_notification:
                self._handle_notification(method, message)

                return 202, None

            return self._handle_request(method, message, request_id, modern)

        except Exception:
            logger.exception("处理 MCP 请求失败：%s", method)

            return 200, make_error(request_id, INTERNAL_ERROR, "Internal server error")

    def _handle_notification(self, method: str, message: dict):
        # legacy 客户端在握手后会发 notifications/initialized。
        # 我们没有会话状态需要初始化，收下即可
        if method in ("notifications/initialized", "initialized", "notifications/cancelled"):
            return

        logger.debug("忽略未知的 MCP 通知：%s", method)

    def _handle_request(self, method: str, message: dict, request_id, modern: bool):
        params = message.get("params") or {}

        match method:
            case "server/discover":
                return 200, make_result(request_id, self._discover())

            case "initialize":
                # legacy 握手。回 echo 客户端请求的版本（若我们支持），
                # 否则给出我们支持的最新 legacy 版本
                requested = params.get("protocolVersion", "")

                negotiated = requested if requested in SUPPORTED_VERSIONS else LEGACY_VERSIONS[0]

                return 200, make_result(request_id, {
                    "protocolVersion": negotiated,
                    "capabilities": {"tools": {"listChanged": False}},
                    "serverInfo": self._server_info(),
                    "instructions": SERVER_INSTRUCTIONS,
                })

            case "ping":
                return 200, make_result(request_id, {})

            case "tools/list":
                result = {"tools": self.tools.list_schemas()}

                # 缓存提示只属于 modern 协议，legacy 结果不带 resultType，
                # 自然也不该带这两个字段
                if modern:
                    result["resultType"] = "complete"
                    result["ttlMs"] = TOOLS_CACHE_TTL_MS
                    result["cacheScope"] = CACHE_SCOPE

                return 200, make_result(request_id, result)

            case "tools/call":
                return self._call_tool(params, request_id, modern)

            case _:
                # 规范要求未实现的方法回 HTTP 404 加 -32601，而不是 200。
                # JSON-RPC 错误体用于把这种情况与"根本不是 MCP 端点"的 404 区分开
                return 404, make_error(request_id, METHOD_NOT_FOUND, f"Method not found: {method}")

    def _discover(self):
        return {
            "resultType": "complete",
            "supportedVersions": SUPPORTED_VERSIONS,
            "capabilities": {"tools": {"listChanged": False}},
            "instructions": SERVER_INSTRUCTIONS,
            "ttlMs": DISCOVER_CACHE_TTL_MS,
            "cacheScope": CACHE_SCOPE,
            "_meta": {SERVER_INFO_KEY: self._server_info()},
        }

    def _server_info(self):
        return {"name": config.app_name, "version": config.app_version}

    def _call_tool(self, params: dict, request_id, modern: bool):
        name = params.get("name")

        if not isinstance(name, str):
            return 200, make_error(request_id, INVALID_PARAMS, "Missing tool name")

        if not self.tools.has(name):
            return 200, make_error(request_id, INVALID_PARAMS, f"Unknown tool: {name}")

        arguments = params.get("arguments") or {}

        if not isinstance(arguments, dict):
            return 200, make_error(request_id, INVALID_PARAMS, "Tool arguments must be an object")

        # 工具自身的失败走 isError，不走 JSON-RPC error：
        # 规范要求把可自我修正的业务错误交回给模型，用协议错误会让调用方
        # 只看到一句"调用失败"而拿不到原因
        result = self.tools.call(name, arguments)

        if modern:
            result["resultType"] = "complete"

        return 200, make_result(request_id, result)
