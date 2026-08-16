#!/usr/bin/env python3
"""
Bili23 Downloader MCP stdio ↔ HTTP 桥接

程序内置的 MCP 服务器走本地 HTTP。多数客户端可以直接连它（设置界面的
「客户端配置 - 复制」给出的就是这份直连配置），此时不需要本脚本。

以下两种情况才需要它：

  1. 客户端只支持 stdio 传输；
  2. 希望在客户端连接时自动拉起 Bili23 Downloader（HTTP 直连要求程序已在运行）。

用法：

    python mcp_bridge.py --port 23330 --token <token>
    python mcp_bridge.py --port 23330 --token <token> --launch "C:/Path/To/Bili23 Downloader.exe"

端口与令牌也可以经环境变量传入（BILI23_MCP_PORT / BILI23_MCP_TOKEN）。

只依赖标准库，可以用任意 Python 3.8+ 解释器运行。
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

DEFAULT_PORT = 23330

PROTOCOL_VERSION_KEY = "io.modelcontextprotocol/protocolVersion"

# HTTP 头只能承载可见 ASCII。含中文的工具名或参数要按规范用哨兵格式编码
BASE64_PREFIX = "=?base64?"
BASE64_SUFFIX = "?="

def log(message):
    # stdout 是 MCP 消息通道，任何诊断信息都必须走 stderr
    print(f"[mcp_bridge] {message}", file = sys.stderr, flush = True)

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

def port_is_open(port, timeout = 0.5):
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
        sock.settimeout(timeout)

        return sock.connect_ex(("127.0.0.1", port)) == 0

def launch_application(command, port, wait_seconds = 60.0):
    """
    拉起程序并等待端口就绪

    传 --ensure-running 让已在运行的实例保持安静：单实例机制会让新进程唤醒
    老实例后自行退出，不加这个开关的话窗口会被抢到前台，打断用户手头的事
    """
    log(f"端口 {port} 未监听，尝试启动：{command}")

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
            log(f"端口 {self.port} 未监听。请先启动 Bili23 Downloader，或用 --launch 指定程序路径。")

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
        # stdio 传输要求一行一条消息，消息内不得含换行
        sys.stdout.write(json.dumps(payload, ensure_ascii = False) + "\n")
        sys.stdout.flush()

def main():
    parser = argparse.ArgumentParser(description = "Bili23 Downloader MCP stdio bridge")
    parser.add_argument("--port", type = int, default = int(os.environ.get("BILI23_MCP_PORT", DEFAULT_PORT)))
    parser.add_argument("--token", default = os.environ.get("BILI23_MCP_TOKEN", ""))
    parser.add_argument(
        "--launch",
        default = os.environ.get("BILI23_MCP_LAUNCH", ""),
        help = "程序路径，端口未监听时用它拉起 Bili23 Downloader",
    )

    args = parser.parse_args()

    if not args.token:
        log("缺少访问令牌。请用 --token 传入，或设置 BILI23_MCP_TOKEN 环境变量。")
        log("令牌可在「设置 → 高级 → MCP 服务器 → 访问令牌」中复制。")

        return 2

    launch_command = None

    if args.launch:
        # 允许把解释器与脚本一起传进来，例如 "python D:/Bili23/src/main.py"
        launch_command = args.launch.split() if " " in args.launch and not os.path.exists(args.launch) else [args.launch]

    bridge = Bridge(args.port, args.token, launch_command)

    try:
        bridge.run()

    except KeyboardInterrupt:
        pass

    return 0

if __name__ == "__main__":
    sys.exit(main())
