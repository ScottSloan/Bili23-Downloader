from ..common.config import config, DefaultValue
from ..common.enum import Area

from urllib.parse import urlparse
from threading import Lock
from copy import deepcopy
import logging
import time

logger = logging.getLogger(__name__)

# 连续探测失败达到该次数的节点，会在 HOST_COOLDOWN 秒内被降到候选列表末尾。
# 批量下载时几百个任务各自生成一遍候选列表，若不共享节点状态，同一个不可达节点会被
# 每个任务重新踩一遍，每次都要白等一整轮超时 —— 这正是批量下载偶发失败的主要来源。
# 注意这里只降权、不丢弃：探测失败的原因也可能是本机网络临时中断，
# 一旦把节点直接剔除，网络恢复后候选列表反而会变空
HOST_FAILURE_THRESHOLD = 2
HOST_COOLDOWN = 180

class HostHealth:
    # 节点健康状态，跨任务共享。解析任务跑在全局线程池上，读写一律加锁
    _lock = Lock()
    _failures: dict[str, int] = {}
    _cooldown_until: dict[str, float] = {}

    @classmethod
    def report_success(cls, host: str):
        if not host:
            return

        with cls._lock:
            cls._failures.pop(host, None)
            cls._cooldown_until.pop(host, None)

    @classmethod
    def report_failure(cls, host: str):
        if not host:
            return

        with cls._lock:
            count = cls._failures.get(host, 0) + 1
            cls._failures[host] = count

            if count >= HOST_FAILURE_THRESHOLD:
                cls._cooldown_until[host] = time.monotonic() + HOST_COOLDOWN

                logger.warning("节点 %s 连续 %s 次探测失败，%s 秒内降低优先级", host, count, HOST_COOLDOWN)

    @classmethod
    def is_cooling(cls, host: str) -> bool:
        if not host:
            return False

        with cls._lock:
            until = cls._cooldown_until.get(host)

            if until is None:
                return False

            if time.monotonic() >= until:
                # 冷却到期，清掉计数重新给它机会
                cls._cooldown_until.pop(host, None)
                cls._failures.pop(host, None)

                return False

            return True

class CDN:
    @staticmethod
    def get_url_tiers(url_list: list[str]) -> tuple[list[str], list[str]]:
        # 返回两层候选链接：第一层按用户偏好优先尝试，第二层兜底。
        # 分层的意义在于让兜底层拿到独立的时间预算 —— 原先所有候选共用一份预算，
        # 替换节点集体超时就会把预算耗光，B 站原始调度链接一次都轮不到，
        # 明明有可用链接却整个任务失败。具体预算分配见 download_url.resolve_download_url
        filtered_url_list = CDN.filter(url_list)

        if not filtered_url_list:
            # 少数视频 B 站只返回 PCDN 链接，全部过滤掉会让候选列表为空，
            # 一次探测都不做就直接失败。此时退回原始链接，劣质链接也好过没有链接
            logger.warning("过滤后没有剩余链接，已退回未过滤的原始链接列表")

            filtered_url_list = [url for url in url_list if url]

        replaced_url_list = CDN.replace(filtered_url_list)

        if config.get(config.prefer_cdn_server_provider):
            # 替换后的链接优先，B 站原始调度链接作为兜底
            primary, fallback = replaced_url_list, filtered_url_list
        else:
            primary, fallback = filtered_url_list, replaced_url_list

        primary = CDN.arrange(primary)
        fallback = CDN.arrange(fallback, exclude = set(primary))

        return primary, fallback

    @staticmethod
    def arrange(url_list: list[str], exclude: set[str] = None) -> list[str]:
        # 去重（保持顺序），并把冷却中的节点整体挪到末尾
        healthy = []
        cooling = []

        for url in dict.fromkeys(url_list):
            if not url or (exclude and url in exclude):
                continue

            if HostHealth.is_cooling(CDN.get_netloc(url)):
                cooling.append(url)
            else:
                healthy.append(url)

        return healthy + cooling

    @staticmethod
    def filter(url_list: list[str]) -> list[str]:
        # 过滤 pcdn、mcdn 等劣质链接
        filtered_url_list = []

        blacklist = [
            "mcdn",
            "pcdn",
            "szbdyd.com",
            "mountaintoys.cn",
        ]

        for url in url_list:
            if not url:
                continue

            # 只匹配主机名，不要拿整条 URL 去做子串匹配：查询参数里出现同样的字样会误杀
            netloc = CDN.get_netloc(url)

            if any(domain in netloc for domain in blacklist):
                continue

            filtered_url_list.append(url)

        return filtered_url_list

    @staticmethod
    def replace(url_list: list[str]) -> list[str]:
        new_url_list = []

        # 取一份快照：这里拿到的是配置里的同一个 list 对象，
        # 用户此刻正在设置界面里增删节点的话，边遍历边修改会直接抛异常
        cdn_server_list = list(CDN.get_cdn_server_list() or [])

        for url in url_list:
            for entry in cdn_server_list:
                node = entry.get("host")

                if not node:
                    continue

                new_url = CDN.replace_netloc(url, node)
                new_url_list.append(new_url)

        return new_url_list

    @staticmethod
    def replace_netloc(url: str, new_netloc: str) -> str:
        parsed_url = urlparse(url)

        if new_netloc == parsed_url.netloc:
            return url

        new_parsed_url = parsed_url._replace(netloc = new_netloc)

        return new_parsed_url.geturl()

    @staticmethod
    def get_netloc(url: str) -> str:
        try:
            return urlparse(url).netloc

        except Exception:
            return ""

    @staticmethod
    def get_cdn_server_list():
        if config.get(config.area) == Area.CN:
            return config.get(config.cn_cdn_server_list)
        else:
            return config.get(config.ov_cdn_server_list)

    @staticmethod
    def set_cdn_server_list(cdn_list: list[dict]):
        if config.get(config.area) == Area.CN:
            config.set(config.cn_cdn_server_list, cdn_list)
        else:
            config.set(config.ov_cdn_server_list, cdn_list)

    @staticmethod
    def get_default_cdn_server_list() -> list[dict]:
        # 必须返回深拷贝：调用方会原地编辑其中的 dict，直接返回会把默认值本身改掉
        if config.get(config.area) == Area.CN:
            return deepcopy(DefaultValue.cn_cdn_server_list)
        else:
            return deepcopy(DefaultValue.ov_cdn_server_list)
