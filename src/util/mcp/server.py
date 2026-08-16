from ..common.config import config

from .protocol import (
    Dispatcher, make_error, HEADER_MISMATCH, PARSE_ERROR, INVALID_REQUEST,
    MODERN_VERSION, SUPPORTED_VERSIONS, is_modern_request, unsupported_version_error,
)

from http.server import HTTPServer, BaseHTTPRequestHandler
from threading import Event, Thread
import binascii
import base64
import secrets
import logging
import json

logger = logging.getLogger(__name__)

ENDPOINT_PATH = "/mcp"

# 请求体上限。工具参数都很小，超出这个量级的只可能是异常或恶意请求
MAX_BODY_SIZE = 1024 * 1024

BASE64_PREFIX = "=?base64?"
BASE64_SUFFIX = "?="

def generate_token() -> str:
    return secrets.token_urlsafe(32)

def decode_header_value(value: str) -> str:
    """
    解码请求头中的 Base64 哨兵值

    含非 ASCII 或前后空白的参数值无法直接放进 HTTP 头，规范定义了
    =?base64?<payload>?= 这一形式承载它们。做头与 body 的一致性比对前必须先解码
    """
    if not (value.startswith(BASE64_PREFIX) and value.endswith(BASE64_SUFFIX)):
        return value

    payload = value[len(BASE64_PREFIX):-len(BASE64_SUFFIX)]

    try:
        return base64.b64decode(payload).decode("utf-8")

    except (binascii.Error, UnicodeDecodeError, ValueError):
        # 解不开就原样返回，后续的一致性比对会因不匹配而拒绝该请求
        return value

def is_origin_allowed(origin: str) -> bool:
    """
    校验 Origin

    规范强制要求：不校验的话，任意网页都能通过 DNS rebinding 驱动用户本机上的
    MCP 服务器。非浏览器客户端不发 Origin，缺失是允许的；一旦存在就必须是本地来源
    """
    if not origin:
        return True

    if origin == "null":
        return False

    for prefix in ("http://localhost", "http://127.0.0.1", "http://[::1]"):
        if origin == prefix or origin.startswith(prefix + ":"):
            return True

    return False

class MCPRequestHandler(BaseHTTPRequestHandler):
    # 该值会出现在响应的 Server 头里
    server_version = "Bili23-MCP"
    sys_version = ""

    protocol_version = "HTTP/1.1"

    def handle_one_request(self):
        try:
            super().handle_one_request()

        finally:
            self._force_close()

    def _force_close(self):
        # 处理完一个请求就断开连接。
        #
        # 服务是单线程串行的（一个 handle_request 一次一个连接），而 HTTP/1.1
        # 默认保持连接：handler 会在响应发出后继续阻塞在 rfile.readline() 上等待
        # 同一连接的下一个请求。server.timeout 只作用于 accept，管不到这里，
        # 于是一个不主动关闭连接的客户端就能把整个服务器占住，后续请求全部卡死。
        #
        # 工具调用之间本就有模型思考的间隔，复用连接省下的那点握手开销没有意义
        self.close_connection = True

    @property
    def dispatcher(self) -> Dispatcher:
        return self.server.dispatcher

    def log_message(self, format, *args):
        # 默认实现直接写 stderr，绕过了本项目的 logging 配置
        logger.debug("MCP %s", format % args)

    def do_GET(self):
        # 2026-07-28 起不再有 GET 流端点；旧客户端的 GET 按规范回 405
        self._send_plain(405, "Method Not Allowed")

    def do_DELETE(self):
        # 协议级 session 已移除，没有可供终止的会话
        self._send_plain(405, "Method Not Allowed")

    def do_POST(self):
        if not is_origin_allowed(self.headers.get("Origin", "")):
            logger.warning("拒绝来源不合法的 MCP 请求：%s", self.headers.get("Origin"))

            self._send_plain(403, "Forbidden")

            return

        if self.path.split("?")[0].rstrip("/") not in ("", ENDPOINT_PATH):
            self._send_plain(404, "Not Found")

            return

        if not self._check_auth():
            return

        body = self._read_body()

        if body is None:
            return

        try:
            message = json.loads(body)

        except (json.JSONDecodeError, UnicodeDecodeError):
            self._send_json(400, make_error(None, PARSE_ERROR, "Invalid JSON"))

            return

        if not isinstance(message, dict):
            # 批量请求（JSON 数组）在 Streamable HTTP 下不被允许
            self._send_json(400, make_error(None, INVALID_REQUEST, "Expected a single JSON-RPC message"))

            return

        if error := self._check_headers(message):
            self._send_json(400, error)

            return

        status, response = self.dispatcher.handle(message)

        if response is None:
            self._send_plain(status, "")

            return

        self._send_json(status, response)

    def _check_auth(self) -> bool:
        expected = config.get(config.mcp_token)

        provided = self.headers.get("Authorization", "")

        prefix = "Bearer "

        token = provided[len(prefix):] if provided.startswith(prefix) else ""

        # 定长比较，避免以耗时差异反推 token
        if not expected or not secrets.compare_digest(token, expected):
            self.send_response(401)
            self.send_header("WWW-Authenticate", 'Bearer realm="Bili23 Downloader MCP"')
            self.send_header("Content-Length", "0")
            self.send_header("Connection", "close")
            self.end_headers()

            return False

        return True

    def _read_body(self):
        try:
            length = int(self.headers.get("Content-Length", 0))

        except ValueError:
            self._send_plain(400, "Bad Request")

            return None

        if length <= 0:
            self._send_json(400, make_error(None, INVALID_REQUEST, "Empty request body"))

            return None

        if length > MAX_BODY_SIZE:
            self._send_plain(413, "Payload Too Large")

            return None

        return self.rfile.read(length)

    def _check_headers(self, message: dict):
        """
        校验镜像到 HTTP 头的字段与请求体是否一致

        规范要求服务端做这项校验：中间层（网关、负载均衡）按头做路由，服务端按
        body 执行，两者不一致就成了可被利用的错位。

        对 legacy 客户端放宽：那一代协议没有这些头，强制要求会直接把它们挡在门外
        """
        modern = is_modern_request(message)

        version_header = self.headers.get("MCP-Protocol-Version", "")

        if modern:
            if not version_header:
                return make_error(message.get("id"), HEADER_MISMATCH, "Missing MCP-Protocol-Version header")

            body_version = (message.get("params") or {}).get("_meta", {}).get(
                "io.modelcontextprotocol/protocolVersion", ""
            )

            if version_header != body_version:
                return make_error(
                    message.get("id"), HEADER_MISMATCH,
                    f"MCP-Protocol-Version header '{version_header}' does not match body value '{body_version}'"
                )

        if version_header and version_header not in SUPPORTED_VERSIONS:
            return unsupported_version_error(message.get("id"), version_header)

        method_header = self.headers.get("Mcp-Method", "")

        if modern and not method_header:
            return make_error(message.get("id"), HEADER_MISMATCH, "Missing Mcp-Method header")

        if method_header and method_header != message.get("method"):
            return make_error(
                message.get("id"), HEADER_MISMATCH,
                f"Mcp-Method header '{method_header}' does not match body method '{message.get('method')}'"
            )

        # Mcp-Name 只对携带名称的方法有意义
        if message.get("method") == "tools/call":
            name_header = self.headers.get("Mcp-Name", "")

            body_name = (message.get("params") or {}).get("name", "")

            if modern and not name_header:
                return make_error(message.get("id"), HEADER_MISMATCH, "Missing Mcp-Name header")

            if name_header and decode_header_value(name_header) != body_name:
                return make_error(
                    message.get("id"), HEADER_MISMATCH,
                    f"Mcp-Name header does not match body value '{body_name}'"
                )

        return None

    def _send_json(self, status: int, payload: dict):
        data = json.dumps(payload, ensure_ascii = False).encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(data)))
        # 让客户端一并知道不要复用连接，见 handle_one_request 的说明
        self.send_header("Connection", "close")
        self.end_headers()

        try:
            self.wfile.write(data)

        except (BrokenPipeError, ConnectionResetError):
            # 客户端取消请求时直接断开，属于正常情况
            logger.debug("MCP 客户端在响应写出前断开")

    def _send_plain(self, status: int, text: str):
        data = text.encode("utf-8")

        self.send_response(status)
        self.send_header("Content-Type", "text/plain; charset=utf-8")
        self.send_header("Content-Length", str(len(data)))
        self.send_header("Connection", "close")
        self.end_headers()

        try:
            if data:
                self.wfile.write(data)

        except (BrokenPipeError, ConnectionResetError):
            logger.debug("MCP 客户端在响应写出前断开")

class MCPHTTPServer(HTTPServer):
    # 端口在快速重启时可能仍处于 TIME_WAIT
    allow_reuse_address = True

    def __init__(self, address, handler, dispatcher):
        super().__init__(address, handler)

        self.dispatcher = dispatcher

class MCPServerManager:
    """
    MCP 服务器的生命周期管理

    沿用 util/auth/server.py 的形态：服务跑在后台线程上，用 stop_event 配合
    server.timeout 做可中断的轮询，避免退出时线程卡在 accept 上。

    请求是串行处理的（一个 handle_request 一次一个连接）。工具调用本就要回到
    GUI 线程执行，并发接入只会让排队发生在更难观察的地方
    """
    def __init__(self):
        self.thread: Thread = None
        self.stop_event: Event = None
        self.server: MCPHTTPServer = None

    @property
    def running(self) -> bool:
        return self.thread is not None and self.thread.is_alive()

    def start(self) -> bool:
        if self.running:
            return True

        if not config.get(config.mcp_enabled):
            return False

        from .invoke import clear_shutdown

        clear_shutdown()

        token = config.get(config.mcp_token)

        if not token:
            token = generate_token()

            config.set(config.mcp_token, token)

        port = config.get(config.mcp_port)

        from .tools import build_registry

        dispatcher = Dispatcher(build_registry())

        try:
            # 只绑环回地址，不监听 0.0.0.0
            self.server = MCPHTTPServer(("127.0.0.1", port), MCPRequestHandler, dispatcher)

        except OSError as e:
            # 端口被占用不能拖垮程序启动，只记录并让设置界面显示出来
            logger.error("MCP 服务器启动失败，端口 %d：%s", port, e)

            config.mcp_running = False
            config.mcp_last_error = str(e)

            return False

        self.server.timeout = 0.5

        self.stop_event = Event()

        self.thread = Thread(target = self._serve, name = "mcp-server", daemon = True)
        self.thread.start()

        config.mcp_running = True
        config.mcp_last_error = ""

        logger.info("MCP 服务器已启动，监听 127.0.0.1:%d", port)

        return True

    def _serve(self):
        try:
            while not self.stop_event.is_set():
                self.server.handle_request()

        except Exception:
            logger.exception("MCP 服务器循环异常退出")

        finally:
            try:
                self.server.server_close()

            except Exception:
                logger.exception("关闭 MCP 服务器套接字失败")

    def stop(self, timeout: float = 2.0):
        # 先让在途请求放弃等待。此刻 GUI 事件循环已在收尾，投递过去的任务不会
        # 再被执行，不短路的话 HTTP 线程会一直等到超时，把退出流程拖住
        from .invoke import begin_shutdown

        begin_shutdown()

        if not self.running:
            self._reset()

            return

        self.stop_event.set()

        # handle_request 最多阻塞 server.timeout 秒，因此这里总能在预算内收敛。
        # 必须真正等到线程退出：退出流程随后会走 shutdown_process，
        # 让一个仍在运行的线程被解释器清理掉就是崩溃
        self.thread.join(timeout)

        if self.thread.is_alive():
            logger.warning("MCP 服务器线程未能在 %.1fs 内退出", timeout)

        self._reset()

        logger.info("MCP 服务器已停止")

    def _reset(self):
        self.thread = None
        self.stop_event = None
        self.server = None

        config.mcp_running = False

    def restart(self):
        self.stop()

        return self.start()

mcp_server_manager = MCPServerManager()
