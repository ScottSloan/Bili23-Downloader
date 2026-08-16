from ...common.data import url_patterns

from ..invoke import call_in_main_thread

from . import text_result, error_result

from threading import Event
import logging

logger = logging.getLogger(__name__)

# 解析结果可能有上千项（合集、个人空间），一次全塞给模型既超长又没用
DEFAULT_LIMIT = 100
MAX_LIMIT = 500

def get_parse_interface():
    from PySide6.QtWidgets import QApplication

    app = QApplication.instance()

    window = getattr(app, "window", None)

    if window is None:
        return None

    return getattr(window, "parse_interface", None)

def _episode_to_dict(item) -> dict:
    from ...parse.episode.tree import Attribute

    data = {
        "episode_id": item.episode_id,
        "title": item.title,
        "number": item.number,
        "duration": item.duration,
    }

    if item.badge:
        data["badge"] = item.badge

    if item.bvid:
        data["bvid"] = item.bvid

    # 需要二次解析的条目（个人空间、收藏夹里的视频）不能直接下载，
    # 必须让模型看见，否则它会拿着这些 id 去创建任务然后困惑于失败
    if item.attribute & Attribute.NEED_PARSE_BIT:
        data["needs_reparse"] = True

    if item.downloaded:
        data["already_downloaded"] = True

    return data

def _media_info_error():
    """媒体信息是否可用，不可用时给出原因（供 create_download 复用同一判断）"""
    from ...parse.preview.info import PreviewerInfo

    if PreviewerInfo.error_occurred:
        return PreviewerInfo.error_message or "media information was not retrieved"

    return None

def _collect_episodes(limit: int):
    interface = get_parse_interface()

    if interface is None:
        return None, 0

    items = interface.parse_list.get_all_items()

    return [_episode_to_dict(item) for item in items[:limit]], len(items)

def _parse_busy_reason():
    """
    检查当前是否适合发起解析

    EpisodeData 是全局缓存，解析开始时会 clear_cache()，界面上的解析树也会被
    整棵替换。用户正勾选着一批要下载的条目时，AI 的解析会把它们连同缓存一起冲掉，
    且不可撤销。这里在入口拦下来，让模型知道要等用户。

    注意不能用 EpisodeData._active_parsers 判断：那个计数只防并发写互相擦除数据，
    防不了"新解析覆盖旧结果"这件事本身。
    """
    interface = get_parse_interface()

    if interface is None:
        return "The application window is not ready yet."

    if interface.parse_list.get_checked_items_count() > 0:
        return (
            "The user currently has items selected in the parse list. Parsing a new link "
            "would discard that selection. Ask the user to finish or clear it first."
        )

    return None

def _do_parse(url: str, timeout: float, preview_timeout: float = 30.0):
    """
    发起解析，并等到媒体信息（清晰度、音质）也就绪

    解析成功只代表拿到了剧集列表。清晰度、音质是随后由 Previewer 异步取的，
    而创建下载任务依赖它 —— 界面上用户要花时间勾选，等于天然等过了这一步，
    但模型是连着调 parse_url 和 create_download 的，不等就必然撞上
    "Media information is not available"。
    """
    from ...common.signal_bus import signal_bus
    from ...thread.async_ import AsyncTask
    from ...parse.worker import ParseWorker

    outcome = {}
    done = Event()
    preview_done = Event()

    def on_success(category_name, extra_data):
        outcome["category"] = category_name
        done.set()

    def on_error(message):
        outcome["error"] = message
        done.set()

    def on_preview_finish():
        preview_done.set()

    def start():
        interface = get_parse_interface()

        # 预览信号必须赶在解析发起之前接上：媒体信息可能来得很快，
        # 晚一步连接就会彻底错过这次通知
        signal_bus.parse.preview_finish.connect(on_preview_finish)

        # 复刻 ParseInterface.on_parse 的启动步骤，额外挂上自己的回调。
        # 不直接调 reparse()：那样拿不到 worker 的 success / error 信号，
        # 解析失败时只能干等到超时，模型看不到真正的原因
        interface.url_box.setText(url)
        interface.parse_btn.setIndeterminateState(True)

        worker = ParseWorker(url, 1)

        worker.success.connect(interface.on_parse_success)
        worker.error.connect(interface.on_parse_error)

        # 这两个回调在解析线程上直连执行，只写字典和置位 Event，不碰 Qt 对象
        worker.success.connect(on_success)
        worker.error.connect(on_error)

        AsyncTask.run(worker)

    call_in_main_thread(start, timeout = 10.0)

    try:
        if not done.wait(timeout):
            return {"error": f"Parsing timed out after {timeout:.0f}s."}

        if "error" not in outcome:
            # 拿不到媒体信息不算解析失败：剧集列表仍然可用，
            # 只是下载会受影响，交由 create_download 去报告
            if not preview_done.wait(preview_timeout):
                logger.warning("等待媒体信息超时，链接：%s", url)

        return outcome

    finally:
        try:
            call_in_main_thread(
                signal_bus.parse.preview_finish.disconnect, on_preview_finish, timeout = 5.0
            )

        except Exception:
            logger.exception("断开预览完成信号失败")

def tool_parse_url(arguments: dict) -> dict:
    url = (arguments.get("url") or "").strip()

    if not url:
        return error_result("The 'url' argument is required.")

    if not any(pattern.search(url) for _, pattern in url_patterns):
        return error_result(
            f"'{url}' is not a recognized Bilibili link. Accepted forms include a full "
            "bilibili.com URL, a b23.tv short link, or a bare av / BV / ep / ss / md id."
        )

    if reason := call_in_main_thread(_parse_busy_reason, timeout = 5.0):
        return error_result(reason)

    limit = _clamp_limit(arguments.get("limit"))

    outcome = _do_parse(url, timeout = 90.0)

    if error := outcome.get("error"):
        return error_result(f"Parsing failed: {error}")

    # 这次调用会排在界面的 on_update_parse_list 之后执行（两者都投递到 GUI
    # 线程的事件循环，先进先出），所以读到的一定是已经更新过的树
    episodes, total = call_in_main_thread(_collect_episodes, limit, timeout = 15.0)

    if episodes is None:
        return error_result("The parse list is unavailable.")

    structured = {
        "category": outcome.get("category", ""),
        "total": total,
        "returned": len(episodes),
        "episodes": episodes,
    }

    media_error = call_in_main_thread(_media_info_error, timeout = 5.0)

    if media_error:
        # 明确告诉模型下载会失败，省得它拿着 episode_id 去撞 create_download
        structured["media_info_available"] = False
        structured["media_info_error"] = media_error

    summary = f"Parsed {total} item(s) from {url}."

    if media_error:
        summary += f" Media information is unavailable ({media_error}), so downloads cannot be created yet."

    if len(episodes) < total:
        summary += f" Showing the first {len(episodes)}; call get_episodes with a higher limit to see more."

    return text_result(summary, structured)

def tool_get_episodes(arguments: dict) -> dict:
    limit = _clamp_limit(arguments.get("limit"))

    episodes, total = call_in_main_thread(_collect_episodes, limit, timeout = 15.0)

    if episodes is None:
        return error_result("The parse list is unavailable.")

    if not total:
        return text_result("The parse list is empty. Call parse_url first.", {
            "total": 0,
            "returned": 0,
            "episodes": [],
        })

    return text_result(f"{total} item(s) in the parse list.", {
        "total": total,
        "returned": len(episodes),
        "episodes": episodes,
    })

def _clamp_limit(value) -> int:
    if not isinstance(value, int) or isinstance(value, bool):
        return DEFAULT_LIMIT

    return max(1, min(value, MAX_LIMIT))

_LIMIT_SCHEMA = {
    "type": "integer",
    "description": f"Maximum number of episodes to return (1-{MAX_LIMIT}, default {DEFAULT_LIMIT}).",
    "minimum": 1,
    "maximum": MAX_LIMIT,
}

def register(registry):
    registry.register(
        name = "parse_url",
        title = "Parse Bilibili Link",
        description = (
            "Parse a Bilibili link and load its episodes into the application's parse list. "
            "Accepts a full URL, a b23.tv short link, or a bare av / BV / ep / ss / md id. "
            "This replaces whatever is currently in the parse list, and is refused while the "
            "user has items selected there. Call this before create_download."
        ),
        input_schema = {
            "type": "object",
            "properties": {
                "url": {
                    "type": "string",
                    "description": "The Bilibili link or id to parse.",
                },
                "limit": _LIMIT_SCHEMA,
            },
            "required": ["url"],
            "additionalProperties": False,
        },
        handler = tool_parse_url,
    )

    registry.register(
        name = "get_episodes",
        title = "List Parsed Episodes",
        description = (
            "List the episodes currently loaded in the application's parse list, including "
            "the episode_id values needed by create_download."
        ),
        input_schema = {
            "type": "object",
            "properties": {"limit": _LIMIT_SCHEMA},
            "additionalProperties": False,
        },
        handler = tool_get_episodes,
    )
