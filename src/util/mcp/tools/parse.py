from ...common.data import url_patterns

from ..invoke import call_in_main_thread

from . import text_result, error_result

from threading import Event, Lock
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

def build_item_index(items) -> dict:
    """
    条目在解析列表中的位置就是它对外的 id

    不能拿 TreeItem.episode_id 当键：那是 EpisodeData 里**视频级**元数据的缓存键，
    同一个视频的所有分P 共享同一个值（分P 之间只有 cid 不同），多集番剧同理。
    用它建索引，10 个分P 会在字典里互相覆盖只剩最后一条 —— 模型想下第 3P，
    实际拿到第 10P，而且全程没有任何报错。

    位置是纯局部标识，只在本次解析结果内有效；解析新链接后列表整体替换，
    编号自然跟着换，与"id 指向当前列表"的语义一致。
    """
    return {str(position): item for position, item in enumerate(items, 1)}

def _episode_to_dict(item_id: str, item, is_link_target: bool = False) -> dict:
    from ...parse.episode.tree import Attribute

    data = {
        "episode_id": item_id,
        "title": item.title,
        "number": item.number,
        "duration": item.duration,
    }

    # 解析的链接精确指向的就是这一条。界面上它会被自动滚动到、自动勾选，
    # 模型手上却只有一份看起来齐平的列表：一个视频的所有分P 共享同一个 bvid，
    # 番剧一整季的条目在导出字段上也毫无差别，不点出来就无从分辨
    if is_link_target:
        data["is_link_target"] = True

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

def _media_info_summary():
    """
    本次解析的内容实际提供哪些清晰度、音质与编码，以及这些信息取自哪个视频

    模型要在 create_download 里指定画质，但它无从知道这个视频有没有 4K。
    不告诉它的话，它只能凭标题猜，猜错了会被静默降级到最接近的档位 ——
    它以为下到了 4K，实际是 1080P，而且没有任何迹象可循。

    首选项是充电专属、付费等取不到媒体信息的视频时，Previewer 会自动换用备选，
    于是这些档位其实属于列表里的**另一个**视频。界面把这件事写在下载选项对话框上，
    模型同样需要知道，否则它会把别人的 4K 当成自己要下的那一集的。

    这几个 choice_data 由 Previewer 填充，解析开始时会被重置成空，
    因此只有在媒体信息就绪后取到的值才有意义。一次取齐是为了让选项与来源
    出自同一个快照：分两次回主线程取，中间用户切换剧集就会把两者对不上。
    """
    from ...parse.preview.info import PreviewerInfo

    options = {}

    for key, data in (
        ("video_quality", PreviewerInfo.video_quality_choice_data),
        ("audio_quality", PreviewerInfo.audio_quality_choice_data),
        ("video_codec", PreviewerInfo.video_codec_choice_data),
    ):
        # 重置时置成的是空列表，解析后才是 {名称: id} 的字典，两种都能取键
        if names := list(data):
            options[key] = names

    source = {}

    if PreviewerInfo.episode_title:
        source["title"] = PreviewerInfo.episode_title

        if PreviewerInfo.episode_number:
            source["number"] = PreviewerInfo.episode_number

        if PreviewerInfo.from_fallback:
            source["from_fallback"] = True

    return options, source

def _collect_episodes(limit: int):
    """
    汇总解析列表的当前内容，界面不可用时返回 None

    返回的字典直接构成工具结果的主体，键序即模型读到的顺序：
    先是规模与链接指向哪一项，再是条目本身
    """
    interface = get_parse_interface()

    if interface is None:
        return None

    items = interface.parse_list.get_all_items()

    # 先按完整列表编号再截断，保证 limit 不会改变任何条目的 id
    index = build_item_index(items)

    link_target_id = _locate_link_target(interface, index)

    episodes = [
        _episode_to_dict(item_id, item, is_link_target = item_id == link_target_id)
        for item_id, item in list(index.items())[:limit]
    ]

    result = {
        "total": len(items),
        "returned": len(episodes),
    }

    if link_target_id is not None:
        result["link_target_episode_id"] = link_target_id

        # 目标项落在 limit 之外时单独附上它的完整信息。这恰恰是最需要它的场景 ——
        # 三百集的合集，链接指向第 250 集 —— 只给一个编号，模型没法跟用户确认
        # 要下的是哪一集，还得再花一轮 get_episodes 去捞
        if not any(episode["episode_id"] == link_target_id for episode in episodes):
            result["link_target_episode"] = _episode_to_dict(
                link_target_id, index[link_target_id], is_link_target = True
            )

    result["episodes"] = episodes

    return result

def _locate_link_target(interface, index: dict):
    """
    解析的链接精确指向的那一项在列表中的位置，链接未指向具体视频时为 None

    投稿视频按 cid、番剧与课程按 ep_id、会员购课程按 section_id 定位，解析侧已经
    算好并交给了解析树（见 ParseTreeView.update_tree），这里只是把结果取出来。

    按对象身份比对而不是比字段：分P 之间除了 cid 什么都一样，番剧一整季的条目
    在导出字段上同样难分彼此，只有对象本身能唯一确定是哪一条。index 里的对象与
    get_current_episode_item() 返回的都来自同一棵树，比对是可靠的
    """
    current_item = interface.parse_list.get_current_episode_item()

    if current_item is None:
        return None

    return next(
        (item_id for item_id, item in index.items() if item is current_item), None
    )

# MCP 上一次解析结束时界面的状态指纹：(全部条目 id, 被勾选的条目 id)
#
# 用户开着自动选择（config.auto_select_mode）时，解析完成后条目会被自动勾上，
# 于是"有勾选项"这个信号会被我们自己上一次解析污染 —— 不加区分的话，
# 第二次 parse_url 起就会永远被守卫拒绝，模型只能解析一次。
#
# 用指纹把两种勾选分开：与指纹完全一致，说明是上次解析留下的自动勾选、
# 用户没碰过，可以安全覆盖；对不上，才是用户真的在挑东西。
_last_snapshot = None

# 解析的互斥锁。解析全程都在动全局状态，两个解析交叠必然互相破坏，
# 详见 tool_parse_url 里的说明。它同时也保护了上面那个指纹变量
_parse_lock = Lock()

def _take_snapshot(interface):
    parse_list = interface.parse_list

    return (
        frozenset(item.episode_id for item in parse_list.get_all_items()),
        frozenset(item.episode_id for item in parse_list.get_checked_items()),
    )

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

    if interface.parse_list.get_checked_items_count() == 0:
        return None

    # 勾选状态与上次解析结束时完全一致 —— 是自动选择留下的，不是用户挑的
    if _last_snapshot is not None and _take_snapshot(interface) == _last_snapshot:
        return None

    return (
        "The user currently has items selected in the parse list. Parsing a new link "
        "would discard that selection. Ask the user to finish or clear it first."
    )

def _record_snapshot():
    global _last_snapshot

    def take():
        interface = get_parse_interface()

        return _take_snapshot(interface) if interface is not None else None

    try:
        _last_snapshot = call_in_main_thread(take, timeout = 5.0)

    except Exception:
        # 取不到就置空，退回"有勾选就拒绝"的保守行为
        logger.exception("记录解析列表状态失败")

        _last_snapshot = None

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

        # 无论成功、失败还是超时都重新取一次指纹：它记的是"界面此刻的样子"，
        # 只有反映真实状态才能在下次解析时正确区分自动勾选与用户勾选。
        # 放在等预览之后，此时自动选择已经应用完毕
        _record_snapshot()

def tool_parse_url(arguments: dict) -> dict:
    url = (arguments.get("url") or "").strip()

    if not url:
        return error_result("The 'url' argument is required.")

    if not any(pattern.search(url) for _, pattern in url_patterns):
        return error_result(
            f"'{url}' is not a recognized Bilibili link. Accepted forms include a full "
            "bilibili.com URL, a b23.tv short link, or a bare av / BV / ep / ss / md id."
        )

    # 服务器改成每连接一个线程后，并发的解析请求会真正并行跑进来，而解析全程
    # 都在动全局状态：EpisodeData 缓存、界面上那一棵解析树、预览完成信号的
    # 连接与断开。两个解析交叠会互相擦掉结果，preview_finish 更会同时唤醒
    # 两边的等待，各自都以为自己的媒体信息已经就绪。
    #
    # 这类串行是数据结构决定的，不是线程调度能优化掉的，所以直接互斥。
    # 只读的工具（任务列表、任务状态、登录状态）不受这把锁影响，仍可并发。
    if not _parse_lock.acquire(timeout = 2.0):
        return error_result(
            "Another parse is already running. Only one parse can run at a time because "
            "it replaces the application's parse list. Retry once it finishes."
        )

    try:
        return _parse_url_locked(url, arguments)

    finally:
        _parse_lock.release()

def _parse_url_locked(url: str, arguments: dict) -> dict:
    if reason := call_in_main_thread(_parse_busy_reason, timeout = 5.0):
        return error_result(reason)

    limit = _clamp_limit(arguments.get("limit"))

    outcome = _do_parse(url, timeout = 90.0)

    if error := outcome.get("error"):
        return error_result(f"Parsing failed: {error}")

    # 这次调用会排在界面的 on_update_parse_list 之后执行（两者都投递到 GUI
    # 线程的事件循环，先进先出），所以读到的一定是已经更新过的树
    collected = call_in_main_thread(_collect_episodes, limit, timeout = 15.0)

    if collected is None:
        return error_result("The parse list is unavailable.")

    structured = {"category": outcome.get("category", "")}
    structured.update(collected)

    total = collected["total"]
    returned = collected["returned"]

    media_error = call_in_main_thread(_media_info_error, timeout = 5.0)

    source = {}

    if media_error:
        # 明确告诉模型下载会失败，省得它拿着 episode_id 去撞 create_download
        structured["media_info_available"] = False
        structured["media_info_error"] = media_error

    else:
        # 供 create_download 的 options 使用：只有这里列出的档位是真实可选的
        options, source = call_in_main_thread(_media_info_summary, timeout = 5.0)

        if options:
            structured["available"] = options

        if source:
            structured["media_info_source"] = source

    summary = f"Parsed {total} item(s) from {url}." + _link_target_note(collected)

    if media_error:
        summary += f" Media information is unavailable ({media_error}), so downloads cannot be created yet."

    else:
        summary += _fallback_note(source)

    if returned < total:
        summary += f" Showing the first {returned}; call get_episodes with a higher limit to see more."

    return text_result(summary, structured)

def tool_get_episodes(arguments: dict) -> dict:
    limit = _clamp_limit(arguments.get("limit"))

    collected = call_in_main_thread(_collect_episodes, limit, timeout = 15.0)

    if collected is None:
        return error_result("The parse list is unavailable.")

    total = collected["total"]

    if not total:
        return text_result("The parse list is empty. Call parse_url first.", {
            "total": 0,
            "returned": 0,
            "episodes": [],
        })

    structured = collected

    options, source = call_in_main_thread(_media_info_summary, timeout = 5.0)

    if options:
        structured["available"] = options

    if source:
        structured["media_info_source"] = source

    summary = f"{total} item(s) in the parse list."

    return text_result(summary + _link_target_note(collected) + _fallback_note(source), structured)

def _link_target_note(collected: dict) -> str:
    """
    把"链接指向的是哪一项"也写进文本摘要

    结构化结果里已经有 is_link_target 与 link_target_episode_id，但并非所有
    MCP 客户端都会把 structuredContent 交给模型，文本是唯一保证送达的那一份
    """
    item_id = collected.get("link_target_episode_id")

    if item_id is None:
        return ""

    episode = collected.get("link_target_episode") or next(
        (item for item in collected["episodes"] if item["episode_id"] == item_id), None
    )

    if title := (episode or {}).get("title"):
        return f" The link points to episode_id {item_id} ({title})."

    return f" The link points to episode_id {item_id}."

def _fallback_note(source: dict) -> str:
    """媒体信息取自别的视频时明说，别让模型把这些档位当成目标视频的"""
    if not source.get("from_fallback"):
        return ""

    return (
        " Note: the linked item did not provide media information, so the qualities in "
        f"'available' are those of another item ({source.get('title', '')}) and may differ "
        "from what the item you download actually offers."
    )

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
            "user has items selected there. Call this before create_download. The result's "
            "'available' field lists the qualities and codecs this content actually offers, "
            "which are the valid values for create_download's options. When the link points at "
            "one specific item of a multi-part video, season or collection, 'link_target_episode_id' "
            "names it (and that item carries 'is_link_target'); prefer it over guessing from titles, "
            "since every part of a video shares one bvid. Its absence means the link addressed the "
            "whole listing rather than a single item."
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
            "the episode_id values needed by create_download, and 'link_target_episode_id' "
            "identifying which item the parsed link pointed at, when it pointed at one."
        ),
        input_schema = {
            "type": "object",
            "properties": {"limit": _LIMIT_SCHEMA},
            "additionalProperties": False,
        },
        handler = tool_get_episodes,
    )
