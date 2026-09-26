from PySide6.QtCore import QCoreApplication, QThread

from ...common.enum import ParserType, ToastNotificationCategory
from ...common.translator import Translator
from ...common.signal_bus import signal_bus
from ...common._json import dumps
from ...common.config import config
from ...common.runtime import runtime

from ..search_url import extract_keyword

from functools import reduce
from hashlib import md5
from threading import Lock
import urllib.parse
import logging
import time
import re

logger = logging.getLogger(__name__)

mixinKeyEncTab = [
    46, 47, 18, 2, 53, 8, 23, 32, 15, 50, 10, 31, 58, 3, 45, 35, 27, 43, 5, 49,
    33, 9, 42, 19, 29, 28, 14, 39, 12, 38, 41, 13, 37, 48, 7, 16, 24, 55, 40,
    61, 26, 17, 0, 1, 60, 51, 30, 4, 22, 25, 54, 21, 56, 59, 6, 63, 57, 62, 11,
    36, 20, 34, 44, 52
]

VIDEO_PLAYURL_API = "https://api.bilibili.com/x/player/wbi/playurl"

NAV_API = "https://api.bilibili.com/x/web-interface/nav"

# getMixinKey 按 mixinKeyEncTab 逐位取值，要取到表里最大的那个下标，原始串就不能短于这个长度。
# 两个 key 正常各 32 位，拼起来 64 位；只有一边拿到、或两边都没拿到时才会短于它
WBI_KEY_LENGTH = max(mixinKeyEncTab) + 1

# 补取密钥的并发控制。解析线程池里可能同时有几十个线程都发现密钥是空的，
# 只让第一个真的发请求，其余的在这把锁上等它的结果
_wbi_fetch_lock = Lock()

# 上次尝试补取的时间戳（time.monotonic）。失败之后短时间内不再打同一个接口：
# nav 有限流，几十个线程排队重打只会把风控招来
_last_fetch_attempt = 0.0
FETCH_THROTTLE_SECONDS = 30.0

def on_gui_thread() -> bool:
    app = QCoreApplication.instance()

    return app is not None and QThread.currentThread() == app.thread()

def wbi_keys_ready() -> bool:
    """密钥是否已经就绪。解析界面据此决定是直接发起解析，还是先等密钥到位"""
    return len(config.get(config.img_key)) + len(config.get(config.sub_key)) >= WBI_KEY_LENGTH

def ensure_wbi_keys():
    """
    确保签名密钥就绪，拿不到就抛一句能读的话。

    密钥本该由启动时的 nav 请求写好（util/auth/user.py），但那次请求可能超时，
    也可能返回一个不带 wbi_img 的响应 —— 弱网下这不是小概率事件。与其让所有
    带 wbi 签名的接口瘫到用户重启为止，不如在第一次真正需要签名时补取一次。

    拿不到时抛的是可读的提示，而不是让 getMixinKey 下标越界：后者报出来的
    "string index out of range" 与网络毫无关系，用户无从归因。
    """
    if wbi_keys_ready():
        return

    # 补取要发同步请求，最长可能阻塞十几秒，而本函数可能在 GUI 线程上被调用 ——
    # 预览面板拼取流地址就是（Previewer.get_video_info 由 GUI 线程的信号驱动）。
    # 那里必须让路：宁可报错，也不能把界面冻住。
    #
    # 正常流程不受影响：解析一定先于预览跑，密钥在解析阶段就补上了，
    # 真正走到这里的是「解析还没开始就被要求签名」这一类边角情况
    if on_gui_thread():
        raise RuntimeError(Translator.ERROR_MESSAGES("WBI_KEY_UNAVAILABLE"))

    with _wbi_fetch_lock:
        # 等锁期间可能已经有别的线程补好了
        if wbi_keys_ready():
            return

        if not _fetch_wbi_keys():
            raise RuntimeError(Translator.ERROR_MESSAGES("WBI_KEY_UNAVAILABLE"))

def _fetch_wbi_keys() -> bool:
    global _last_fetch_attempt

    now = time.monotonic()

    if now - _last_fetch_attempt < FETCH_THROTTLE_SECONDS:
        return False

    _last_fetch_attempt = now

    # 惰性导入：util/parse/parser/base.py 是纯逻辑模块，不希望因为补取密钥这一条
    # 边角路径，就把网络栈拉进它的顶层导入图
    from ...auth.base import store_wbi_keys
    from ...network.request import SyncNetWorkRequest

    try:
        response = SyncNetWorkRequest(NAV_API).run()

    except Exception:
        logger.warning("补取 wbi 签名密钥失败", exc_info = True)

        return False

    if not store_wbi_keys(response.get("data") or {}):
        logger.warning("补取 wbi 签名密钥失败：响应里没有 wbi_img")

        return False

    logger.info("wbi 签名密钥已补取")

    return True

def enc_wbi(params: dict):
    def getMixinKey(orig: str):
        return reduce(lambda s, i: s + orig[i], mixinKeyEncTab, "")[:32]

    ensure_wbi_keys()

    mixin_key = getMixinKey(config.get(config.img_key) + config.get(config.sub_key))
    curr_time = round(time.time())

    params["wts"] = curr_time
    params = dict(sorted(params.items()))
    params = {
        k : "".join(filter(lambda chr: chr not in "!'()*", str(v)))
        for k, v
        in params.items()
    }

    query = urllib.parse.urlencode(params)
    wbi_sign = md5((query + mixin_key).encode()).hexdigest()
    params["w_rid"] = wbi_sign

    return urllib.parse.urlencode(params)

def build_video_info_url(bvid: str, cid: int, quality_id: int):
    # 做成模块级函数是因为按需补取视频流的两处调用方（预览、下载的 VideoInfoParser）
    # 都不是 ParserBase 的子类，却同样需要构造带 wbi 签名的 playurl 地址
    params = {
        "bvid": bvid,
        "cid": cid,
        "qn": quality_id,
        "fnver": 0,
        "fnval": 4048,
        "fourk": 1,
    }

    return f"{VIDEO_PLAYURL_API}?{enc_wbi(params)}"

class ParserBase:
    def __init__(self):
        self.url = ""
        self.info_data = {}

        # 停止标记，用于跳转链接时停止当前解析流程
        self.stop_flag = False
        # 是否抛出异常
        self.raise_for_status = True

        self.error_message = ""

    def get_url_keyword(self):
        """
        从链接中提取搜索关键词，供支持服务端搜索的解析类型使用。

        关键词跟随链接传递，因此翻页与自动解析分页无需额外处理即可保持搜索状态。
        """
        return extract_keyword(self.url)

    def set_search_keyword(self, keyword: str):
        """
        把搜索关键词一并放进接口数据，供 episode 解析器在节点标题中标注。

        自动解析分页复用的也是这份数据，因此无需再单独传递。
        """
        self.info_data["data"]["_search_keyword"] = keyword

    def find_str(self, pattern: str, url: str, check: bool = True):
        result = re.findall(pattern, url)
        
        if result:
            return result[0]
        
        elif check:
            raise ValueError("无效的链接")

    def enc_wbi(self, params: dict):
        return enc_wbi(params)

    def _build_video_info_url(self, bvid: str, cid: int, quality_id: int):
        return build_video_info_url(bvid, cid, quality_id)

    def on_error(self, message: str):
        self.error_message = message

        logger.error(message)

    def check_response(self, response: dict):
        if self.error_message:
            raise RuntimeError(self.error_message)
        
        if response.get("code", -1) != 0:
            logger.error("接口请求错误：\n{response}".format(
                response = dumps(response, indent = 2)
                )
            )

            raise RuntimeError(response.get("message", "未知错误"))
    
    def get_extra_data(self) -> dict:
        return {}
    
    def get_parser_type(self) -> ParserType:
        return ParserType.UNKNOWN
    
    def get_category_name(self) -> str:
        return self.get_parser_type().value
    
    def check_login(self):
        if not config.get(config.is_login) or runtime.auth.is_expired:
            signal_bus.toast.show_long_message.emit(
                ToastNotificationCategory.ERROR,
                Translator.ERROR_MESSAGES("LOGIN_REQUIRED"),
                Translator.ERROR_MESSAGES("LOGIN_REQUIRED_MESSAGE")
            )

            raise RuntimeError(Translator.ERROR_MESSAGES("LOGIN_REQUIRED_MESSAGE"))
