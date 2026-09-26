"""
检查新版本 —— 不依赖 Qt 的那一半

`update.py` 里的 `Updater` 是 QObject，走 Qt 线程与 signal_bus，那属于桌面侧。
WebUI 后端跑在 asyncio 循环里，用不了它。

而**「问服务端有没有新版本」这件事本身与界面无关**：发一个请求、读一份响应、
判断要不要更新。这部分放在这里两端共用，请求交给 Verhub SDK —— 接口路径、
请求体形状、平台声明、错误响应的判别都由 SDK 按服务端契约维护，不再各写一遍。

更新说明按界面语言取译文：服务端命中项目注册的语言就返回对应译文，
没注册或没有译文时回落到默认内容，所以语言偏好总是可以放心带上。
"""

from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

VERHUB_BASE_URL = "https://verhub.hanloth.cn/api/v1"
VERHUB_PROJECT_KEY = "scottsloan-bili23-downloader"

LOCALE_ZH_CN = "zh-CN"
LOCALE_ZH_TW = "zh-TW"
LOCALE_EN_US = "en-US"

# 这些地区/书写系统子标签对应繁体界面，与 main.py 装载翻译文件时的判定一致
TRADITIONAL_CHINESE_SUBTAGS = {"tw", "hk", "mo", "hant"}

def to_verhub_locale(language: Optional[str]) -> Optional[str]:
    """
    把界面语言换成提交给服务端的语言标签

    接受 config.json 里的字面量（`zh_CN`、`Auto`）、Qt 的 `QLocale.name()`（`zh_HK`）
    与浏览器的 BCP-47 标签（`zh-Hant-TW`、`en`）

    `Auto` 与空值返回 None，即不提语言偏好，服务端给默认内容
    """
    if not language:
        return None

    tag = language.strip().replace("_", "-").lower()

    if not tag or tag == "auto":
        return None

    subtags = tag.split("-")

    if subtags[0] == "zh":
        return LOCALE_ZH_TW if TRADITIONAL_CHINESE_SUBTAGS.intersection(subtags[1:]) else LOCALE_ZH_CN

    return LOCALE_EN_US

def _create_client():
    """
    按当前的代理设置建一个客户端

    每次检查都新建：代理可以在运行中改，检查更新又是低频操作，缓存客户端
    反而要处理「代理改了连接池没跟上」。连接走应用自己的代理与证书配置，
    不用全局那个 client —— 那上面带着 B 站的 Cookie，没必要让它经过别的服务
    """
    import httpx

    from verhub_sdk import VerhubClient

    from ..common.config import config
    from ..network.request import get_proxy_mounts, get_ssl_context, get_timeout

    http_client = httpx.Client(
        timeout = get_timeout(),
        mounts = get_proxy_mounts(),
        follow_redirects = True,
        verify = get_ssl_context()
    )

    client = VerhubClient(
        VERHUB_BASE_URL,
        VERHUB_PROJECT_KEY,
        timeout = get_timeout(),
        http_client = http_client,
        # 保留 SDK 自己的 User-Agent，后面追加应用标识，服务端统计两边都看得到
        app_identifier = f"Bili23-Downloader/{config.app_version}",
        # 只用检查更新，不做事件采集。显式关掉本地持久化，保证 SDK 不在用户设备上写任何东西
        analytics = {"persistence": "none"}
    )

    return client, http_client

def parse_response(response: dict) -> dict:
    """把服务端的响应摊成界面要用的那几个字段"""
    latest = response["latest_version"]

    return {
        "should_update": bool(response["should_update"]),
        "required": bool(response["required"]),
        "version": latest["version"],
        "content": latest.get("content") or "",
        "update_url": latest.get("download_url") or "",
    }

def check_for_update(include_preview: bool = False, locale: Optional[str] = None) -> Tuple[Optional[dict], Optional[str]]:
    """
    阻塞地问一次服务端。返回 (结果, 出错说明)，两者必有其一为 None

    `locale` 是界面语言（写法见 `to_verhub_locale`），决定更新说明用哪个语言。
    桌面侧在 Qt 线程里调，WebUI 后端扔进后台线程池调
    """
    from ..common.config import config
    from ..common.translator import Translator

    client = http_client = None

    try:
        # 建客户端也放进 try：SDK 缺失（运行时模板没带上）时只算这次没问成，不能让后台线程崩掉
        client, http_client = _create_client()

        response = client.public.check_update(
            current_version = config.app_version,
            current_comparable_version = config.app_comparable_version,
            include_preview = include_preview,
            locale = to_verhub_locale(locale)
        )

        return parse_response(response), None

    except Exception as e:
        logger.warning("检查更新失败：%s", e)

        return None, str(e) or Translator.ERROR_MESSAGES("UNKNOWN_ERROR")

    finally:
        if client:
            client.close()

        if http_client:
            http_client.close()
