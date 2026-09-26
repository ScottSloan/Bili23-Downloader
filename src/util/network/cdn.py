from ..common.config import config, DefaultValue
from ..common.enum import Area

from urllib.parse import urlparse
from threading import Lock
from copy import deepcopy
import logging
import time
from typing import ClassVar

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
    _failures: ClassVar[dict[str, int]] = {}
    _cooldown_until: ClassVar[dict[str, float]] = {}

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
    def get_candidate_urls(url_list: list[str]) -> list[str]:
        # 返回一份**有序**的候选列表：用户偏好的那一层排在前，另一层兜底排在后面。
        #
        # 这里刻意只表达顺序，不再像以前那样切成两层、各给一份时间预算。分层预算会把兜底层
        # 饿死：首选层用满自己的份额时，兜底层连一批请求都发不完就撞上总预算，候选一多就表现
        # 为"候选 24 个、实际只试了 12 个"直接报错 —— 而那 12 个既不是探测失败也不是被跳过，
        # 只是根本没来得及发出去。探测侧现在对整份列表做一次滑动窗口扫描，
        # 见 download_url._probe_candidates
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

        # 两次 arrange 分开调用、最后拼接，而不是 arrange(primary + fallback)：
        # 后者会把两层的冷却节点一起挪到同一个末尾，冷却的首选层链接会排到健康的兜底层链接
        # 之后，等于把"首选层优先"悄悄换成"健康的优先"。扁平化之后顺序是唯一承载用户偏好的
        # 东西，不能再被 arrange 重新洗一遍
        primary = CDN.arrange(primary)

        return primary + CDN.arrange(fallback, exclude = set(primary))

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
            # mirror14b 虽然挂在 upos- 前缀下，实测却是 P2P 节点而非普通镜像：
            # 它不响应 HEAD（返回 404），直连 GET 会以 RemoteProtocolError 断开连接，
            # 只有经由代理才返回正常分片。探测它必然得出失败结论，白白消耗一次往返，
            # 因此直接在候选阶段剔除。（同批对照的 mirror08c、mirrorcoso1 均正常返回 200）
            "upos-sz-mirror14b.bilivideo.com",
            # 以下两个域名取自 bilibili-accelerator 的 P2P 实测名单。本机采样 60 个视频
            # 未出现，属预防性收录：名单若有偏差也只是这条规则不生效，不会误伤正常节点
            "nexusedgeio.com",
            "ahdohpiechei.com",
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
    def is_mall_course_url(url: str) -> bool:
        # 会员购商城课程的视频存在单独的存储桶里，只有部分节点有这份数据：
        # 这类链接直接跳过节点替换
        return "/mallxcodeboss/" in url or "gen=playurlv2_itemsvideo" in url

    @staticmethod
    def replace(url_list: list[str]) -> list[str]:
        new_url_list = []

        # 取一份快照：这里拿到的是配置里的同一个 list 对象，
        # 用户此刻正在设置界面里增删节点的话，边遍历边修改会直接抛异常
        cdn_server_list = list(CDN.get_cdn_server_list() or [])

        for url in url_list:
            if CDN.is_mall_course_url(url):
                continue

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

        except ValueError:
            # 畸形的 IPv6 字面量会让 urlparse 抛 ValueError，取不到就按空处理；
            # 其余异常（如传入非字符串）属于调用方错误，应当正常暴露
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
