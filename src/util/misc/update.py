from PySide6.QtCore import QLocale, QObject, Signal, Slot

from ..common.enum import Language, ToastNotificationCategory
from ..common.signal_bus import signal_bus
from ..common.translator import Translator
from ..thread.async_ import AsyncTask
from ..common.config import config

from typing import Optional, Tuple
import logging

logger = logging.getLogger(__name__)

VERHUB_BASE_URL = "https://verhub.hanloth.cn/api/v1"
VERHUB_PROJECT_KEY = "scottsloan-bili23-downloader"

LOCALE_ZH_CN = "zh-CN"
LOCALE_ZH_TW = "zh-TW"
LOCALE_EN_US = "en-US"

TRADITIONAL_CHINESE_SUBTAGS = {"tw", "hk", "mo", "hant"}

def get_ui_language() -> str:
    """
    界面实际显示的语言

    设为跟随系统时，main.py 按 `QLocale()` 装载翻译文件，这里同样取系统语言，
    更新说明才会与界面是同一种语言
    """
    language = config.get(config.language)

    # Language 的枚举值是 QLocale（见 enum.py），要取 .name() 才是字符串；
    # 直接返回 .value 会在非"跟随系统"时把 QLocale 对象传下去，
    # 下面 to_verhub_locale() 一调 .strip() 就炸
    return QLocale.system().name() if language == Language.AUTO else language.value.name()

def to_verhub_locale(language: Optional[str]) -> Optional[str]:
    """
    把界面语言换成提交给服务端的语言标签

    接受 config.json 里的字面量（`zh_CN`、`Auto`）、Qt 的 `QLocale.name()`（`zh_HK`）
    与浏览器的 BCP-47 标签（`zh-Hant-TW`、`en`）

    `Auto` 与空值返回 None，即不提语言偏好，服务端给默认内容
    """
    tag = (language or "").strip().replace("_", "-").lower()

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

class UpdateCheckWorker(QObject):
    # manual 随请求一起带上，而不是让 Updater 用一个共享实例属性记«这次是不是手动查»——
    # 自动检查（启动时）与手动检查（设置页点击）可能同时在飞，谁的响应先回来，
    # 共享属性就会被后到的那次请求覆盖，导致跳过版本被绕过或"已是最新"提示丢失
    success = Signal(dict, bool)
    error = Signal(str)
    finished = Signal()

    def __init__(self, include_preview: bool, locale: str, manual: bool):
        super().__init__()

        self.include_preview = include_preview
        self.locale = locale
        self.manual = manual

    @Slot()
    def run(self):
        try:
            info, error_message = check_for_update(self.include_preview, self.locale)

            if error_message:
                self.error.emit(error_message)
            else:
                self.success.emit(info, self.manual)

        finally:
            self.finished.emit()

class Updater(QObject):
    def __init__(self, parent = None):
        super().__init__(parent)

    def check(self, info: dict, manual: bool):
        version = info["version"]

        if info.get("should_update"):

            if config.get(config.skip_version) == version and not manual:
                return

            signal_bus.update.show_dialog.emit(info)

            logger.info("检测到新版本：%s，当前版本：%s", version, config.app_version)

        else:
            if manual:
                signal_bus.toast.show.emit(ToastNotificationCategory.SUCCESS, "", Translator.TIP_MESSAGES("ALREADY_LATEST_VERSION"))

    def on_error(self, error_message: str):
        logger.error("检查更新失败：%s", error_message)

        signal_bus.toast.show_long_message.emit(
            ToastNotificationCategory.ERROR,
            Translator.ERROR_MESSAGES("CHECK_UPDATE_FAILED"),
            error_message
        )

    def request_update(self, manual: bool):
        worker = UpdateCheckWorker(config.get(config.include_prerelease), get_ui_language(), manual)
        worker.success.connect(self.check)
        worker.error.connect(self.on_error)

        AsyncTask.run(worker)