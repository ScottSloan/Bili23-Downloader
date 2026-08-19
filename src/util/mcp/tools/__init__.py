from ..invoke import MainThreadTimeout

from typing import Callable
import logging
import json

logger = logging.getLogger(__name__)

def text_result(text: str, structured = None, is_error: bool = False) -> dict:
    """
    组装一个工具结果

    带 structuredContent 时同时在 content 里放一份序列化后的 JSON：
    规范要求这么做，未实现结构化内容的客户端才能拿到同样的信息
    """
    result = {
        "content": [{"type": "text", "text": text}],
        "isError": is_error,
    }

    if structured is not None:
        result["structuredContent"] = structured
        result["content"] = [{
            "type": "text",
            "text": json.dumps(structured, ensure_ascii = False, indent = 2),
        }]

        if text:
            result["content"].insert(0, {"type": "text", "text": text})

    return result

def error_result(message: str) -> dict:
    """
    业务失败

    走 isError 而非 JSON-RPC error：规范要求把可自我修正的错误交回模型，
    模型据此调整参数重试；协议错误则只会被当作调用失败
    """
    return text_result(message, is_error = True)

class Tool:
    __slots__ = ("name", "title", "description", "input_schema", "handler")

    def __init__(self, name, title, description, input_schema, handler):
        self.name = name
        self.title = title
        self.description = description
        self.input_schema = input_schema
        self.handler = handler


    def to_schema(self) -> dict:
        return {
            "name": self.name,
            "title": self.title,
            "description": self.description,
            "inputSchema": self.input_schema,
        }

class ToolRegistry:
    def __init__(self):
        self._tools: dict[str, Tool] = {}

    def register(self, name: str, title: str, description: str, input_schema: dict,
                 handler: Callable):
        self._tools[name] = Tool(name, title, description, input_schema, handler)

    def has(self, name: str) -> bool:
        return name in self._tools

    def list_schemas(self) -> list:
        # 顺序固定：规范建议保持确定性排序，客户端才能缓存工具列表
        return [tool.to_schema() for tool in self._tools.values()]

    def call(self, name: str, arguments: dict) -> dict:
        tool = self._tools[name]

        try:
            return tool.handler(arguments)

        except MainThreadTimeout as e:
            logger.warning("MCP 工具 %s 等待主线程超时：%s", name, e)

            return error_result(
                "The application did not respond in time. It may be showing a dialog "
                "that needs attention. Try again after the user has dealt with it."
            )

        except Exception as e:
            logger.exception("MCP 工具执行失败：%s", name)

            return error_result(f"Tool execution failed: {e}")

def build_registry() -> ToolRegistry:
    """
    构造工具注册表

    业务模块在这里才导入，保证 MCP 未启用时不把解析、下载链路拖进启动路径
    """
    from . import parse, download, task

    registry = ToolRegistry()

    parse.register(registry)
    task.register(registry)
    download.register(registry)

    return registry
