"""
util/network/download_url.py —— 下载地址的候选扫描。

打桩掉 `_probe_url` 之后，这个模块就是一段纯粹的调度逻辑：候选有没有被全部发出去过、
同一节点是不是只发一次、命中之后有没有立刻收手、在途并发有没有封顶、没得出结论的候选
有没有被补测。本文件钉的就是这些。

故障背景：候选列表原先被墙钟预算截断（首选层 18 秒、整体 30 秒），撞上黑洞节点时每波要耗掉
连接与读两次超时，于是第 4 波刚开始就整轮放弃 —— 用户看到的是"共 24 个候选，已尝试 12 个"，
而那 12 个既不是探测失败、也不是被跳过，只是根本没来得及发出去。
`test_no_candidate_is_dropped_even_when_the_clock_jumps` 用假时钟把这条钉死：
日后谁再按墙钟放弃候选，它的断言会立刻失败。
"""

from util.network import download_url
from util.network.cdn import CDN, HostHealth

from concurrent.futures import Future
from threading import Event, Lock
import logging
import pytest

# 等一个"应该发生"的事件时的上限。事件在正确实现下毫秒级就会出现，
# 这个值只在实现写错（比如退回整批等齐）时兜底，用来把挂起变成失败
WAIT_TIMEOUT = 2


@pytest.fixture(autouse = True)
def clean_host_health():
    # HostHealth 是跨任务共享的类级状态（冷却 180 秒），不清空的话用例会按执行顺序互相影响：
    # 前一个用例把某节点打进冷却，后一个用例的候选顺序就变了
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
def candidate_list(monkeypatch):
    # 候选列表整体打桩：真实列表由配置里的节点列表推导，而那份配置在同一次会话里会被
    # 其它用例改动，直接用默认值会让本文件的断言取决于执行顺序
    def apply(url_list: list[str]):
        monkeypatch.setattr(CDN, "get_candidate_urls", lambda _: list(url_list))

        return url_list

    return apply


@pytest.fixture
def probe(monkeypatch):
    def apply(url_list: list[str], script: dict = None, reason: str = "ReadTimeout") -> "ProbeStub":
        stub = ProbeStub(url_list, script = script, reason = reason)

        monkeypatch.setattr(download_url, "_probe_url", stub)

        return stub

    return apply


def make_urls(node_count: int, per_node: int = 1) -> list[str]:
    # 与 CDN.replace 一致按"链接在外、节点在内"展开：同一个节点上的多条备份链接在列表中并不相邻，
    # 因此每一波探测都会打到不同的节点上
    return [
        "https://node-{node}.example.com/part-{part}.m4s".format(node = node, part = part)
        for part in range(per_node)
        for node in range(node_count)
    ]


class ProbeStub:
    """假的探测实现：记录被探测的链接与在途并发峰值，按脚本决定每一条的探测结果"""

    def __init__(self, url_list: list[str], script: dict = None, reason: str = "ReadTimeout"):
        # script: url -> [(大小, 失败原因), ...]，按该链接的调用次序取用，用完后固定取最后一项。
        # 未列出的链接一律按 reason 失败
        self.script = script or {}
        self.reason = reason

        self.calls = []
        self.peak = 0
        self.attempts = {}

        self._lock = Lock()
        self._in_flight = 0
        self._index = {url: index for index, url in enumerate(url_list)}
        self._on_call = lambda url: None

    def index_of(self, url: str) -> int:
        return self._index[url]

    def called_hosts(self) -> set[str]:
        return {CDN.get_netloc(url) for url in self.calls}

    def on_call(self, callback):
        """安装一个在每次探测**开始时**执行的钩子，用来制造卡顿或观察顺序"""
        self._on_call = callback

        return self

    def __call__(self, url: str, min_file_size: int) -> tuple[int, str]:
        with self._lock:
            self._in_flight += 1
            self.peak = max(self.peak, self._in_flight)

            self.calls.append(url)
            self.attempts[url] = self.attempts.get(url, 0) + 1

            attempt = self.attempts[url]

        try:
            self._on_call(url)

        finally:
            with self._lock:
                self._in_flight -= 1

        steps = self.script.get(url)

        if steps:
            return steps[min(attempt - 1, len(steps) - 1)]

        return 0, self.reason


class ImmediateExecutor:
    """submit 立刻返回一个已完成的 future。

    用来确定性地制造"同一波里有多个候选同时成功"：真实线程池下一波里有几个 future 会落进
    同一次 wait 的返回值里，取决于线程调度，测不稳
    """

    def __init__(self):
        self.submitted = []

    def submit(self, function, *args):
        future = Future()
        future.set_result(function(*args))

        self.submitted.append(args[0])

        return future


def empty_stats() -> dict:
    return {
        "attempted": 0,
        "skipped": 0,
        "reasons": [],
        "inconclusive": []
    }


class TestCoverage:
    def test_every_node_is_probed_before_giving_up(self, candidate_list, probe, caplog):
        # 4 个节点、每个 3 条候选链接，全部失败
        urls = make_urls(4, per_node = 3)
        candidate_list(urls)

        stub = probe(urls)

        with caplog.at_level(logging.WARNING, logger = "util.network.download_url"):
            with pytest.raises(RuntimeError) as error:
                download_url.resolve_download_url(urls)

        # 每个节点都要真正发出去一次，而不是只试了前几个就整轮报错
        assert stub.called_hosts() == {CDN.get_netloc(url) for url in urls}

        # 候选只有两种去处：真正探测过，或因同节点已经失败而跳过 —— 一个都不能凭空消失。
        # 同节点上多探几条是正常的（同一波里几条链接并发在途，第一条的结果还没回来，
        # 后面的已经发出去了），但两种去处加起来必须等于候选总数
        record = next(record for record in caplog.records if "全部候选链接探测失败" in record.getMessage())

        assert record.args[2] + record.args[3] == record.args[0]

        # 提示按节点口径报数：原先那句"共 12 个候选，已尝试 6 个"读起来像是程序只试了一部分
        assert "12 个候选覆盖 4 个 CDN 节点" in str(error.value)

    def test_no_candidate_is_dropped_even_when_the_clock_jumps(self, candidate_list, probe, monkeypatch):
        # 假时钟：每读一次时间就往前跳 30 秒。旧实现的时间预算（首选层 18 秒 / 整体 30 秒）
        # 会在第一波之后就放弃整轮探测，而这 12 个候选分布在 12 个不同节点上，一个都不该被跳过。
        # 这条同时锁住"探测不受墙钟约束"这个性质：日后谁再加回预算，这里立刻红
        class JumpingClock:
            def __init__(self, step: float = 30.0):
                self.step = step
                self.now = 0.0

            def monotonic(self) -> float:
                self.now += self.step

                return self.now

        urls = make_urls(12)
        candidate_list(urls)

        stub = probe(urls)

        monkeypatch.setattr(download_url, "time", JumpingClock())

        with pytest.raises(RuntimeError):
            download_url.resolve_download_url(urls)

        # 12 个候选分布在 12 个不同节点上，一个都不该被跳过，全都得探测过
        assert sorted(stub.calls) == sorted(urls)

    def test_stops_as_soon_as_one_candidate_works(self, candidate_list, probe):
        urls = make_urls(12)
        candidate_list(urls)

        stub = probe(urls, script = {urls[2]: [(2048, "")]})

        result = download_url.resolve_download_url(urls)

        assert result["url"] == urls[2]
        assert result["file_size"] == 2048

        # 命中之后不再继续扫：至多只有第一波发出去过
        assert len(stub.calls) <= download_url.PROBE_CONCURRENCY

    def test_file_smaller_than_min_size_counts_as_failure(self, candidate_list, probe):
        urls = make_urls(2)
        candidate_list(urls)

        # 预览链路要求 10240 以上：先探到的那条只有 4KB，必须继续找下一条
        probe(urls, script = {urls[0]: [(4096, "")], urls[1]: [(20480, "")]})

        result = download_url.resolve_download_url(urls, min_file_size = 10240)

        assert result["url"] == urls[1]
        assert result["file_size"] == 20480


class TestScheduling:
    def test_window_refills_without_waiting_for_the_slowest(self, candidate_list, probe):
        # 1 号候选立刻失败，2~4 号卡住不动。滑动窗口应当马上补进第 5 个候选；
        # 换成"整批等齐"就会一直等 2~4 号，第 5 个永远发不出去
        urls = make_urls(8)
        candidate_list(urls)

        stub = probe(urls)

        window_opened = Event()
        released_early = []

        def slow_down(url):
            index = stub.index_of(url)

            if index == download_url.PROBE_CONCURRENCY:
                # 第 5 个候选被提交 = 窗口确实在替补，而不是在等整批
                window_opened.set()

            elif 0 < index < download_url.PROBE_CONCURRENCY:
                # 卡住，直到第 5 个候选出现
                released_early.append(window_opened.wait(timeout = WAIT_TIMEOUT))

        stub.on_call(slow_down)

        with pytest.raises(RuntimeError):
            download_url.resolve_download_url(urls)

        # 关键在"提前放行"：整批等齐的实现下，2~4 号只能等到自己超时，
        # 第 5 个候选要等这一批整体结束才会被提交，那时它们早已放弃等待
        assert released_early and all(released_early), "整批等齐：第 5 个候选没有在前 4 个出结果之前补位"
        assert stub.peak == download_url.PROBE_CONCURRENCY

    def test_lowest_index_wins_when_several_succeed_at_once(self, probe):
        # 同一波里多个候选同时成功时，必须取候选列表里靠前的那个。
        # 扁平化之后，用户在设置里排的节点顺序就靠这个"靠前"体现，
        # 而遍历 done 拿到的是 set、顺序不确定，不按下标取就会被它随机决定
        urls = make_urls(4)
        probe(urls, script = {urls[1]: [(2048, "")], urls[3]: [(4096, "")]})

        result = download_url._probe_candidates(ImmediateExecutor(), urls, 1024, set(), empty_stats())

        assert result["url"] == urls[1]
        assert result["file_size"] == 2048


class TestInconclusive:
    def test_inconclusive_candidate_is_probed_again(self, candidate_list, probe):
        # PoolTimeout 源于本机连接池排队，与节点好坏无关：它既不能算节点失败（那会误伤好节点），
        # 也不该像原先那样被静默丢掉 —— 批量下载时几十个任务共用同一个探测 client，
        # 第一轮撞上排队是常态，补测一轮往往就能拿到结论
        urls = make_urls(3)
        candidate_list(urls)

        stub = probe(urls, script = {urls[1]: [(0, "PoolTimeout"), (2048, "")]})

        result = download_url.resolve_download_url(urls)

        assert result["url"] == urls[1]
        assert stub.attempts[urls[1]] == 2

        # 其余候选是确定的失败，不该被无谓地重探
        assert stub.attempts[urls[0]] == 1
        assert stub.attempts[urls[2]] == 1

    def test_inconclusive_does_not_mark_the_node_as_failed(self, candidate_list, probe):
        urls = make_urls(3)
        candidate_list(urls)

        probe(urls, reason = "PoolTimeout")

        with pytest.raises(RuntimeError):
            download_url.resolve_download_url(urls)

        # 整轮都没得出结论，节点健康状态必须原封不动
        assert HostHealth._failures == {}
        assert HostHealth._cooldown_until == {}
