"""
MCP（Model Context Protocol）服务器

在本地环回地址上暴露一个 HTTP 端点，供 AI 客户端调用解析与下载能力。

本模块刻意不在导入期做任何事：MCP 默认关闭，且启动耗时是本项目的硬约束，
相关实现（http.server、解析链路、下载链路）只在真正启用时才被拉进来。
"""

import logging

logger = logging.getLogger(__name__)

def start_mcp_server() -> bool:
    """
    按当前配置启动 MCP 服务器，未启用时静默返回
    """
    from ..common.config import config

    if not config.get(config.mcp_enabled):
        return False

    from .server import mcp_server_manager

    return mcp_server_manager.start()

def stop_mcp_server(timeout: float = 2.0):
    """
    停止 MCP 服务器

    退出流程中调用。服务器从未启动过时不应把模块导入进来，
    因此先看是否已经加载
    """
    import sys

    module = sys.modules.get(f"{__package__}.server")

    if module is None:
        return

    try:
        module.mcp_server_manager.stop(timeout)

    except Exception:
        logger.exception("停止 MCP 服务器失败")

def restart_mcp_server() -> bool:
    """
    应用配置变更（端口、开关、token）后重启服务器
    """
    from ..common.config import config
    from .server import mcp_server_manager

    mcp_server_manager.stop()

    if not config.get(config.mcp_enabled):
        return False

    return mcp_server_manager.start()
