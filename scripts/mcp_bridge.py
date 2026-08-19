#!/usr/bin/env python3
"""
Bili23 Downloader MCP stdio ↔ HTTP 桥接（独立入口）

一般不需要它：只认 stdio 的客户端（如 Claude Desktop）直接把主程序当作
服务器拉起即可，配置见「设置 → 高级 → MCP 服务器 → 客户端配置 → stdio」。

    {"command": "<Bili23 Downloader 路径>", "args": ["--mcp-stdio"]}

保留这个脚本是为了两种场景：想用自己的 Python 解释器跑桥接，或者调试时
需要把桥接与主程序分开观察。实现在 src/util/mcp/stdio_bridge.py 里，
这里只负责把 src 挂到 sys.path 上，避免同一套逻辑维护两份。

用法：

    python scripts/mcp_bridge.py                       # 端口与令牌从配置文件读
    python scripts/mcp_bridge.py --port 23330 --token <token>
"""
import os
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "src"))

from util.mcp.stdio_bridge import run_stdio_bridge

if __name__ == "__main__":
    sys.exit(run_stdio_bridge())
