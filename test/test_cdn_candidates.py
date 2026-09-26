"""
util/network/cdn.py —— 候选链接的组装与排序。

`CDN.get_candidate_urls` 的输出顺序是「用户偏好优先」的**唯一载体**：首选层整体排在兜底层
之前，冷却节点只退到各自那一层的末尾。探测侧按这个顺序提交请求、并在同一波里取下标最小的
成功者，因此顺序一旦写错，用户在设置里排的节点优先级就静默失效 —— 不报错、不崩溃，
只是变得又慢又差，正是最难发现的那种退化。

这些全是纯函数（`filter` / `replace` / `arrange`），用假域名即可覆盖，不需要网络。

另注意 `arrange` 必须**逐层**调用后再拼接，不能对拼接结果调一次：后者会把两层的冷却节点
一起挪到同一个末尾，冷却的首选层链接会排到健康的兜底层链接之后。
`test_cooling_node_only_sinks_within_its_own_layer` 就是钉这条的。
"""

from util.network.cdn import CDN, HostHealth
from util.common.config import config

import pytest

# 候选列表里的主机名全部用假域名，避免与真实节点状态、配置迁移互相干扰
NODES = ["node-a.example.com", "node-b.example.com", "node-c.example.com"]


@pytest.fixture(autouse = True)
def clean_host_health():
    # HostHealth 是跨任务共享的类级状态（冷却 180 秒），不清空的话本文件内的用例会按执行顺序
    # 互相影响：前一个用例把某节点打进冷却，后一个用例的候选顺序就变了
    with HostHealth._lock:
        saved_failures = dict(HostHealth._failures)
        saved_cooldown = dict(HostHealth._cooldown_until)

        HostHealth._failures.clear()
        HostHealth._cooldown_until.clear()

    yield

    with HostHealth._lock:
        HostHealth._failures.clear()
        HostHealth._failures.update(saved_failures)

        HostHealth._cooldown_until.clear()
        HostHealth._cooldown_until.update(saved_cooldown)


@pytest.fixture
def prefer_provider(monkeypatch):
    # 直接打桩 config.get，而不是 config.set 落盘：后者会把测试用的偏好写进配置文件，
    # 而同一次会话里其它用例（如 CDN 列表迁移）也读同一份 config
    def apply(value: bool):
        original_get = config.get

        def fake_get(item):
            if item is config.prefer_cdn_server_provider:
                return value

            return original_get(item)

        monkeypatch.setattr(config, "get", fake_get)

    return apply


@pytest.fixture
def nodes(monkeypatch):
    # 节点列表同样打桩：默认列表会被配置迁移用例改动，且区域判定会决定读国内还是海外那份
    def apply(hosts = None):
        monkeypatch.setattr(CDN, "get_cdn_server_list", lambda: [{"host": host} for host in (hosts or NODES)])

    return apply


def hosts_of(url_list: list[str]) -> list[str]:
    return [CDN.get_netloc(url) for url in url_list]


class TestLayerOrder:
    def test_primary_layer_comes_before_fallback(self, prefer_provider, nodes):
        prefer_provider(True)
        nodes()

        originals = ["https://upos-origin.example.net/video.m4s", "https://upos-backup.example.net/audio.m4s"]

        candidates = CDN.get_candidate_urls(originals)

        # 首选层 = 替换到各个节点的链接，兜底层 = B 站原始调度链接
        assert hosts_of(candidates) == NODES * len(originals) + hosts_of(originals)

    def test_prefer_false_puts_original_links_first(self, prefer_provider, nodes):
        prefer_provider(False)
        nodes()

        originals = ["https://upos-origin.example.net/video.m4s"]

        candidates = CDN.get_candidate_urls(originals)

        assert hosts_of(candidates) == hosts_of(originals) + NODES

    def test_cooling_node_only_sinks_within_its_own_layer(self, prefer_provider, nodes):
        prefer_provider(True)
        nodes()

        originals = ["https://upos-origin.example.net/video.m4s"]

        # 把第一个节点打进冷却（连续失败达到阈值）
        for _ in range(2):
            HostHealth.report_failure(NODES[0])

        candidates = CDN.get_candidate_urls(originals)

        # 冷却节点退到首选层末尾，但**不能**越过兜底层：它仍然是首选层的链接
        assert hosts_of(candidates) == NODES[1:] + [NODES[0]] + hosts_of(originals)


class TestDeduplication:
    def test_same_host_in_both_layers_is_kept_once(self, prefer_provider, nodes):
        prefer_provider(True)
        nodes()

        # B 站原始 baseUrl 的主机名本来就在节点列表里是常态：此时 replace_netloc 原样返回，
        # 兜底层会出现一条与首选层完全相同的链接
        original = "https://{node}/video.m4s".format(node = NODES[0])
        candidates = CDN.get_candidate_urls([original])

        assert candidates.count(original) == 1
        assert len(candidates) == len(NODES)

    def test_backup_links_of_one_resource_collapse_into_one_per_node(self, prefer_provider, nodes):
        prefer_provider(True)
        nodes()

        # baseUrl 与各 backupUrl 指向同一份资源：路径与查询参数都相同，只有主机名不同。
        # 改写到同一个节点之后它们成为同一条链接，因此首选层是按**节点数**算，不是按备份数算。
        # 候选数量少于"节点 × 备份"时别急着找 bug，先看这里
        originals = [
            "https://upos-origin.example.net/upgcxcode/video.m4s?upsig=abc",
            "https://upos-backup.example.net/upgcxcode/video.m4s?upsig=abc"
        ]

        candidates = CDN.get_candidate_urls(originals)

        assert hosts_of(candidates) == NODES + hosts_of(originals)
        assert len(candidates) == len(NODES) + 2


class TestFallbacks:
    def test_mall_course_links_skip_node_replacement(self, prefer_provider, nodes):
        prefer_provider(True)
        nodes()

        # 会员购课程的视频存在单独的存储桶里，只有部分节点有数据，因此跳过节点替换
        original = "https://upos-origin.example.net/mallxcodeboss/video.m4s"

        assert CDN.get_candidate_urls([original]) == [original]

    def test_all_filtered_links_fall_back_to_raw_list(self, prefer_provider, nodes):
        prefer_provider(True)
        nodes()

        # 少数视频 B 站只返回 PCDN 链接：全部被 filter 掉之后必须退回原始列表，
        # 否则一次探测都不做就直接失败
        pcdn = "https://x.pcdn.example.net/video.m4s"
        candidates = CDN.get_candidate_urls([pcdn])

        assert pcdn in candidates
        assert hosts_of(candidates) == NODES + [CDN.get_netloc(pcdn)]

    def test_empty_input_yields_no_candidates(self, prefer_provider, nodes):
        prefer_provider(True)
        nodes()

        assert CDN.get_candidate_urls([]) == []
