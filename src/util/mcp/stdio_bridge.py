"""
stdio ↔ HTTP 桥接

程序内置的 MCP 服务器走本地 HTTP，但部分客户端（如 Claude Desktop）只接受
stdio 传输的服务器：它们的配置里只有 command / args，填 url 会被判为非法条目
直接跳过。这类客户端通过 `--mcp-stdio` 把本程序当作 stdio 服务器拉起，
由这里把 stdin 收到的 JSON-RPC 消息转发给 HTTP 端点，再把响应写回 stdout。

本模块**只用标准库**，且不得导入任何 Qt 或 config 相关的东西 ——
它由 main.py 在最早期调用，此时整个 GUI 栈都还没有加载，
这也正是 stdio 模式的意义：不启动界面，只做一层转发。
"""
import argparse
import base64
import json
import os
import socket
import subprocess
import sys
import time
import urllib.error
import urllib.request

APP_NAME = "Bili23 Downloader"

DEFAULT_PORT = 23330

PROTOCOL_VERSION_KEY = "io.modelcontextprotocol/protocolVersion"

# HTTP 头只能承载可见 ASCII，含中文的工具名要按规范用哨兵格式编码
BASE64_PREFIX = "=?base64?"
BASE64_SUFFIX = "?="

def configure_streams():
    """
    把标准流固定为 UTF-8

    MCP 的 stdio 传输规定消息用 UTF-8 编码，但 Windows 上 Python 的标准流
    默认跟随 locale（简体中文环境是 GBK）。不显式设定的话，含中文的标题写出去
    就是 GBK 字节，客户端按 UTF-8 解析必然是一片乱码。

    这个坑特别隐蔽：开发终端往往设了 PYTHONUTF8 / PYTHONIOENCODING，
    手动测试一切正常；而客户端拉起的是干净环境的子进程，那里才会翻车。

    stdout 的换行一并固定为 \\n —— Windows 的文本模式会把 \\n 写成 \\r\\n，
    而 stdio 传输是以换行分隔消息的。
    """
    try:
        sys.stdin.reconfigure(encoding = "utf-8", errors = "replace")

    except (AttributeError, ValueError):
        pass

    try:
        sys.stdout.reconfigure(encoding = "utf-8", newline = "\n")

    except (AttributeError, ValueError):
        pass

    try:
        sys.stderr.reconfigure(encoding = "utf-8", errors = "replace")

    except (AttributeError, ValueError):
        pass

def log(message):
    # stdout 是 MCP 的消息通道，任何诊断信息都必须走 stderr，
    # 混进去一行日志就会让客户端解析失败
    print(f"[bili23-mcp] {message}", file = sys.stderr, flush = True)

def encode_header_value(value):
    if not isinstance(value, str):
        value = str(value)

    needs_encoding = (
        not value.isascii()
        or any(ord(ch) < 0x20 or ord(ch) == 0x7F for ch in value)
        or value != value.strip()
        or (value.startswith(BASE64_PREFIX) and value.endswith(BASE64_SUFFIX))
    )

    if not needs_encoding:
        return value

    payload = base64.b64encode(value.encode("utf-8")).decode("ascii")

    return f"{BASE64_PREFIX}{payload}{BASE64_SUFFIX}"

def config_path() -> str:
    """
    定位 config.json

    与 QStandardPaths.AppDataLocation + applicationName 的结果保持一致，
    但不引入 Qt。写死这段路径逻辑是有意的：为了读两个配置项去加载
    qfluentwidgets 的 QConfig，会把整个 GUI 依赖链拖进这个本该极轻的进程。
    """
    if sys.platform == "win32":
        base = os.environ.get("APPDATA") or os.path.expanduser("~/AppData/Roaming")

    elif sys.platform == "darwin":
        base = os.path.expanduser("~/Library/Application Support")

    else:
        base = os.environ.get("XDG_DATA_HOME") or os.path.expanduser("~/.local/share")

    return os.path.join(base, APP_NAME, "config.json")

def _dig(node, key):
    """在嵌套的配置结构里找一个键。qfluentwidgets 按分组存，这样找免得分组名一改就失效"""
    if isinstance(node, dict):
        if key in node:
            return node[key]

        for value in node.values():
            if (found := _dig(value, key)) is not None:
                return found

    return None

def load_config():
    """从 config.json 读端口与令牌，读不到时返回 (None, None)"""
    path = config_path()

    try:
        with open(path, "r", encoding = "utf-8") as f:
            data = json.load(f)

    except FileNotFoundError:
        log(f"未找到配置文件：{path}")

        return None, None

    except (OSError, json.JSONDecodeError) as e:
        log(f"读取配置文件失败：{e}")

        return None, None

    return _dig(data, "mcp_port"), _dig(data, "mcp_token")

def port_is_open(port, timeout = 0.5):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)

        return sock.connect_ex(("127.0.0.1", port)) == 0

# src/ 根目录（打包后是 script/），main.py 与 mcp_stdio.py 都在这里
SOURCE_ROOT = os.path.dirname(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

def find_interpreter() -> str:
    """
    开发环境下用来跑入口脚本的解释器

    只服务于"没有打包"这一种情况。打包版一律走启动器（见 find_application），
    不要试图在 runtime 目录里找解释器：Linux 与 macOS 的启动器是把解释器
    编译进自身的，那里根本没有 python 可执行文件。

    优先 pythonw：python.exe 是控制台子系统，客户端拉起时会闪出一个黑框。
    """
    candidate = os.path.join(os.path.dirname(sys.executable), "pythonw.exe")

    return candidate if os.path.exists(candidate) else sys.executable

def find_application() -> str:
    """
    找启动器（打包后的程序本体），未打包时返回空串

    直接读 PYSTAND 环境变量 —— 三个平台的启动器都会在拉起 Python 之前把自身
    路径写进去。不要改成扫描目录找可执行文件：Windows 上是 Bili23.exe，
    Linux 与 macOS 上却是没有扩展名的 bili23-downloader，按后缀匹配必然落空。

    也不能绕开启动器、用解释器直接跑 main.py：程序靠 PYSTAND_HOME 定位
    bundle/ffmpeg，那个变量同样由启动器设置，绕过去的实例找不到内置 FFmpeg；
    何况 Linux / macOS 的发行包里压根没有独立的解释器可用。
    """
    application = os.environ.get("PYSTAND", "")

    return application if application and os.path.exists(application) else ""

def application_command() -> list:
    """拼出"启动本程序"的命令，桥接与拉起都基于它"""
    if application := find_application():
        return [application]

    # 开发环境下没有打包出的 exe，用解释器跑入口脚本
    return [find_interpreter(), os.path.join(SOURCE_ROOT, "main.py")]

def stdio_launch_command() -> list:
    """
    拼出让客户端启动 stdio 桥接的命令，用于生成客户端配置

    Windows 上这依赖 loader 不去接管已被重定向的标准流：早期版本会无条件
    freopen 到控制台、或把 sys.stdout 换成 devnull，那时写入照样"成功"，
    数据却到不了管道对面。修好之前的版本用不了这条路径。
    """
    return application_command() + ["--mcp-stdio"]

def self_launch_command():
    """拼出"启动主程序"的命令"""
    return application_command()

def launch_application(command, port, wait_seconds = 60.0):
    """
    拉起程序并等待端口就绪

    传 --ensure-running 让已在运行的实例保持安静：单实例机制会让新进程唤醒
    老实例后自行退出，不加这个开关的话窗口会被抢到前台，打断用户手头的事
    """
    log(f"端口 {port} 未监听，尝试启动：{' '.join(command)}")

    try:
        subprocess.Popen(
            command + ["--ensure-running"],
            stdin = subprocess.DEVNULL,
            stdout = subprocess.DEVNULL,
            stderr = subprocess.DEVNULL,
        )

    except OSError as e:
        log(f"启动失败：{e}")

        return False

    deadline = time.monotonic() + wait_seconds

    while time.monotonic() < deadline:
        if port_is_open(port):
            log("端口已就绪")

            return True

        time.sleep(0.5)

    log(f"等待 {wait_seconds:.0f}s 后端口仍未就绪")

    return False

class Bridge:
    def __init__(self, port, token, launch_command = None):
        self.url = f"http://127.0.0.1:{port}/mcp"
        self.port = port
        self.token = token
        self.launch_command = launch_command

    def build_headers(self, message):
        headers = {
            "Content-Type": "application/json",
            "Accept": "application/json, text/event-stream",
            "Authorization": f"Bearer {self.token}",
        }

        method = message.get("method")

        if isinstance(method, str):
            headers["Mcp-Method"] = method

        params = message.get("params") or {}

        if isinstance(params, dict):
            meta = params.get("_meta") or {}

            # 只有带 _meta 的 modern 请求才需要版本头；legacy 客户端不发，
            # 服务端对那一代也不做强制校验
            if isinstance(meta, dict) and meta.get(PROTOCOL_VERSION_KEY):
                headers["MCP-Protocol-Version"] = meta[PROTOCOL_VERSION_KEY]

            name = params.get("name") or params.get("uri")

            if isinstance(name, str) and name:
                headers["Mcp-Name"] = encode_header_value(name)

        return headers

    def forward(self, message):
        """把一条消息转发给 HTTP 端点，返回要写回 stdout 的响应（无则返回 None）"""
        data = json.dumps(message).encode("utf-8")

        request = urllib.request.Request(self.url, data = data, method = "POST")

        for key, value in self.build_headers(message).items():
            request.add_header(key, value)

        try:
            with urllib.request.urlopen(request, timeout = 300) as response:
                raw = response.read()

                return json.loads(raw) if raw else None

        except urllib.error.HTTPError as e:
            raw = e.read()

            # 服务端的错误响应本身就是合法的 JSON-RPC error，直接透传，
            # 客户端才能看到真正的原因（版本不支持、头不匹配等）
            try:
                return json.loads(raw) if raw else None

            except json.JSONDecodeError:
                return self._error(message, -32603, f"HTTP {e.code}: {raw[:200].decode('utf-8', 'replace')}")

        except urllib.error.URLError as e:
            return self._error(message, -32603, f"Cannot reach Bili23 Downloader: {e.reason}")

        except socket.timeout:
            return self._error(message, -32603, "Request to Bili23 Downloader timed out")

    def _error(self, message, code, text):
        if "id" not in message:
            return None

        return {"jsonrpc": "2.0", "id": message["id"], "error": {"code": code, "message": text}}

    def ensure_running(self):
        if port_is_open(self.port):
            return True

        if not self.launch_command:
            log(f"端口 {self.port} 未监听，且未指定启动方式。请先启动 Bili23 Downloader。")

            return False

        return launch_application(self.launch_command, self.port)

    def run(self):
        self.ensure_running()

        for line in sys.stdin:
            line = line.strip()

            if not line:
                continue

            try:
                message = json.loads(line)

            except json.JSONDecodeError:
                log("收到非法 JSON，已忽略")

                continue

            if not isinstance(message, dict):
                log("收到非对象消息，已忽略")

                continue

            # 程序可能中途被关掉，每次请求前确认一次比让请求直接失败友好
            if not port_is_open(self.port) and not self.ensure_running():
                if response := self._error(message, -32603, "Bili23 Downloader is not running"):
                    self.write(response)

                continue

            if response := self.forward(message):
                self.write(response)

    def write(self, payload):
        # 一律转义成 \\uXXXX，让写出去的字节永远是纯 ASCII。
        #
        # 规范要求 stdio 传输用 UTF-8，上面也已经把 stdout 固定成 UTF-8 了，
        # 但整条链路上只要有一环按系统编码理解这些字节（Windows 中文环境是
        # GBK），中文标题就会碎成一片乱码，而且是无声的 —— 客户端不会报错，
        # 只会把乱码交给模型。ASCII 在任何单字节或多字节编码下都是同一个字节，
        # JSON 解析器还原 \\uXXXX 后得到的也一定是正确的字符。
        #
        # 代价只是消息体积变大，本地管道传输可以忽略。
        #
        # stdio 传输要求一行一条消息，消息内不得含换行
        sys.stdout.write(json.dumps(payload, ensure_ascii = True) + "\n")
        sys.stdout.flush()

def run_stdio_bridge(argv = None) -> int:
    """
    stdio 桥接入口

    端口与令牌默认从 config.json 读取，这样用户在界面上重新生成令牌之后
    不必再去改一遍客户端配置；命令行参数优先，便于排查问题。
    """
    configure_streams()

    parser = argparse.ArgumentParser(prog = "bili23 --mcp-stdio", add_help = False)
    parser.add_argument("--mcp-stdio", action = "store_true")
    parser.add_argument("--port", type = int, default = None)
    parser.add_argument("--token", default = None)
    parser.add_argument("--no-launch", action = "store_true", help = "端口未监听时不要自动启动程序")

    args, _ = parser.parse_known_args(sys.argv[1:] if argv is None else argv)

    port, token = args.port, args.token

    if port is None or not token:
        config_port, config_token = load_config()

        port = port if port is not None else (config_port or DEFAULT_PORT)
        token = token or config_token

    if not token:
        log("缺少访问令牌：配置文件里没有，也没有通过 --token 传入。")
        log("请先在「设置 → 高级 → MCP 服务器」中启用服务器，令牌会在那里生成。")

        return 2

    bridge = Bridge(port, token, None if args.no_launch else self_launch_command())

    try:
        bridge.run()

    except KeyboardInterrupt:
        pass

    return 0
