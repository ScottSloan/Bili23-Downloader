"""
WebUI 验证用的 REST 垫片

这是 WebUI 开发路线里 S0 阶段的临时产物，只为在不改动任何业务逻辑的前提下，
让前端能拿到真实的解析树，尽早确认交互设计是否成立。**S3 落地 FastAPI 之后
整个文件删除**，不要往这里堆功能。

之所以寄生在 MCP 服务器上：鉴权、Origin 校验、连接管理、跨线程投递这几样
它都已经有了，而且 MCP 工具本就定义好了"从 HTTP 线程安全地驱动解析"的边界，
照搬即可，不必再写一遍。

与 MCP 工具的差异只有一处：工具把解析结果拍平成列表交给模型，
WebUI 要的是带层级的树（合集 → 分P、番剧 → 正片 / PV），因此树的序列化在这里新写。

已知取舍：
- POST /api/parse 是**阻塞**的，解析完才返回。不另起后台线程是因为这个仓库在
  线程生命周期上栽过跟头 —— MCP 的请求线程是非守护且由 server_close() 收敛的，
  借它阻塞比自己开一个没人 join 的线程安全得多。典型解析几秒内返回，最坏 90s。
- 沿用 MCP 的 Bearer 令牌鉴权，因此需要先在设置里启用 MCP 服务。
  正式的密码鉴权在 S3 做。
"""

from ..common.config import config

from .invoke import call_in_main_thread

import logging

logger = logging.getLogger(__name__)

def _get_parse_interface():
    from .tools.parse import get_parse_interface

    return get_parse_interface()

def _check_state(item) -> int:
    """
    Qt.CheckState → 0 / 1 / 2

    TreeItemBase 初始化时存的是枚举，但 set_checked_state 允许传 int，
    历史数据两种都可能出现，统一成数字交给前端
    """
    state = item.checked

    value = state.value if hasattr(state, "value") else state

    return int(value or 0)

def _node_to_dict(item, node_id: str, Attribute) -> dict:
    """
    序列化单个树节点

    node_id 用位置路径（"1"、"1.2"、"1.2.3"）而非 episode_id：后者是 EpisodeData 里
    **视频级**元数据的缓存键，同一个视频的所有分P 共享同一个值，拿它当前端的 key
    会让 10 个分P 互相覆盖。位置路径只在本次解析结果内有效，解析新链接后整棵树替换，
    编号跟着换，与"id 指向当前列表"的语义一致。
    """
    data = {
        "id": node_id,
        "title": item.title,
        "number": item.number,
        "badge": item.badge,
        "duration": item.duration,
        "dyn_time": item.dyn_time,
        "checked": _check_state(item),
        # 树节点（合集标题、章节标题等）只用于分组，本身不可下载
        "is_node": bool(item.attribute & Attribute.TREE_NODE_BIT),
    }

    if item.cover:
        data["cover"] = item.cover

    # 需要二次解析的条目（个人空间、收藏夹里的视频）不能直接下载，界面上要区分出来
    if item.attribute & Attribute.NEED_PARSE_BIT:
        data["needs_reparse"] = True

    if item.downloaded:
        data["already_downloaded"] = True

    if item.children:
        data["children"] = [
            _node_to_dict(child, f"{node_id}.{index}", Attribute)
            for index, child in enumerate(item.children, 1)
        ]

    return data

def _collect_tree() -> dict:
    """
    读取当前解析树。**必须在 GUI 线程执行**：界面随时可能整棵替换它
    """
    from ..parse.episode.tree import Attribute

    interface = _get_parse_interface()

    if interface is None:
        return None

    root = interface.parse_list._model.root_node

    tree = [
        _node_to_dict(child, str(index), Attribute)
        for index, child in enumerate(root.children, 1)
    ]

    return {
        "category": getattr(interface, "category_name", ""),
        # 可下载条目数，与界面上显示的总数一致（不含分组用的树节点）
        "total": len(root.get_all_children()),
        "tree": tree,
    }

def _collect_columns() -> list:
    """
    用户配置的列，让 WebUI 与 GUI 显示同一组列、同样的顺序与宽度

    只给 key，不给列名。列名由前端自己的 i18n 提供（D12）：
    common/translator.py 走的是 QCoreApplication.translate，那是 Qt 的翻译体系，
    WebUI 依赖它等于把桌面端的 .ts / .qm 拖进服务端，且 S2-3 本就要把它去 Qt 化
    """
    return [
        {
            "key": entry.get("attr_key", ""),
            "width": entry.get("width", 0),
            "show": entry.get("show", True),
        }
        for entry in config.get(config.parse_list_column)
    ]

def _collect_status() -> dict:

    interface = _get_parse_interface()

    return {
        "version": config.app_version,
        # 界面语言与 GUI 共用同一个配置项（D5）。只给取值，翻译表两边各自维护（D12）：
        # "Auto" / "zh_CN" / "zh_TW" / "en_US"
        "language": config.language.serialize(),
        "logged_in": bool(config.get(config.is_login)),
        "uname": config.user_uname or "",
        "uid": config.user_uid or "",
        # 给地址而不是图片本身：GUI 侧存的是下载好的 QPixmap，没法直接交给浏览器。
        # 页面已设 referrer=no-referrer，B 站图床不会因缺 Referer 而拒绝
        "face_url": config.user_face_url or "",
        "parse_ready": interface is not None,
    }

def _route_status(payload: dict):
    status = call_in_main_thread(_collect_status, timeout = 5.0)

    status["columns"] = call_in_main_thread(_collect_columns, timeout = 5.0)

    return 200, status

def _route_parse_tree(payload: dict):
    result = call_in_main_thread(_collect_tree, timeout = 15.0)

    if result is None:
        return 503, {"error": "The application window is not ready yet."}

    result["columns"] = call_in_main_thread(_collect_columns, timeout = 5.0)

    return 200, result

def _route_parse(payload: dict):
    from .tools.parse import tool_parse_url

    url = (payload.get("url") or "").strip()

    if not url:
        return 400, {"error": "The 'url' field is required."}

    # 直接借用 MCP 工具：链接校验、解析互斥锁、"用户正勾选着东西时拒绝解析"的守卫、
    # 等媒体信息就绪、解析后重新取界面状态指纹，这一整套都在里面，不要在这里重写。
    # limit 传 1 只是为了让它少做一次无用的拍平，返回的列表这里用不上
    result = tool_parse_url({"url": url, "limit": 1})

    if result.get("isError"):
        message = ""

        for block in result.get("content", []):
            if block.get("type") == "text":
                message = block.get("text", "")

                break

        return 400, {"error": message or "Parsing failed."}

    structured = result.get("structuredContent") or {}

    tree = call_in_main_thread(_collect_tree, timeout = 15.0)

    if tree is None:
        return 503, {"error": "The parse list is unavailable."}

    tree["columns"] = call_in_main_thread(_collect_columns, timeout = 5.0)

    # 媒体信息（清晰度、音质、编码）取不到时，解析本身仍算成功，
    # 但下载会受影响，透传给前端提示用户
    if structured.get("media_info_available") is False:
        tree["media_info_available"] = False
        tree["media_info_error"] = structured.get("media_info_error", "")

    elif available := structured.get("available"):
        tree["available"] = available

    return 200, tree

# (方法, 路径) → 处理函数
_ROUTES = {
    ("GET", "/api/status"): _route_status,
    ("GET", "/api/parse/tree"): _route_parse_tree,
    ("POST", "/api/parse"): _route_parse,
}

def handle_rest(method: str, path: str, payload: dict):
    """
    返回 (状态码, 响应体)。调用方已完成 Origin 校验、鉴权与请求体解析
    """
    handler = _ROUTES.get((method, path.rstrip("/") or path))

    if handler is None:
        return 404, {"error": f"No such endpoint: {method} {path}"}

    try:
        return handler(payload or {})

    except Exception as e:
        logger.exception("REST 请求处理失败：%s %s", method, path)

        return 500, {"error": f"Request failed: {e}"}
