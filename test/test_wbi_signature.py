"""
wbi 签名密钥的获取、失败方式与补救路径。

签名用的两个 key 由 nav 请求写入配置（util/auth/*），正常各 32 位。弱网下那次请求
可能超时，或返回一个不带 data.wbi_img 的响应（风控 -412、未登录 -101），此时 key 会
一直停在配置的默认值空串上，而这两条路径原先都给不出可用的提示：

* util/parse/parser/base.py 的 enc_wbi 里 orig[i] 直接下标越界，抛出的是
  "string index out of range" —— 一条与网络看起来毫无关系、用户也无从归因的错误；
* util/auth/user.py 的 on_get_user_info_success 直接 data["wbi_img"] 取值，
  KeyError 落在 Qt 槽里会被绑定层吞掉，界面上一声不响。

两处都不是崩溃，而是「静默的半瘫」：解析、画质、弹幕、下载一起失败，界面上却只有
一条读不懂的报错，或者什么都没有。因此这里钉住四件事：失败要是一句能读的话、
网络类失败要退避重试、任何一次拿到 nav 响应的地方都要顺手把密钥补回来，
以及真的缺密钥时要能就地补取（而不是等到用户重启）。
"""

import pytest

from util.common.config import config
from util.common.runtime import runtime
from util.common.signal_bus import signal_bus
from util.common.translator import Translator
from util.auth.user import UserManager
from util.parse.parser.base import enc_wbi, ensure_wbi_keys, WBI_KEY_LENGTH

import re
from threading import Thread
from types import SimpleNamespace
from urllib.parse import parse_qsl


IMG_KEY = "a" * 32
SUB_KEY = "b" * 32

WBI_IMG = {
    "img_url": "https://i0.hdslb.com/bfs/wbi/7cd084941338484aae1ad9425b84077c.png",
    "sub_url": "https://i0.hdslb.com/bfs/wbi/4932caff0ff746eab6f01bf08b70ac45.png",
}


@pytest.fixture(autouse = True)
def clean_wbi_keys():
    # 每个用例都从「两个 key 都是空串」这个真实故障现场出发，避免用例之间互相借用状态。
    # is_login 一并压成 False：它决定 on_get_user_info_success 走正常分支还是「登录已过期」
    config.set(config.img_key, "")
    config.set(config.sub_key, "")
    config.set(config.is_login, False)

    yield

    config.set(config.img_key, "")
    config.set(config.sub_key, "")
    config.set(config.is_login, False)


@pytest.fixture(autouse = True)
def app():
    # 必须是 QApplication 而不是 QCoreApplication：进程里一旦先有了后者，
    # 之后需要 QApplication 的 GUI 测试就无法再创建了。
    #
    # 全用例共享（autouse）还有第二个理由：ensure_wbi_keys 按「在不在 GUI 线程上」
    # 分流，而判定依赖 QCoreApplication 实例是否存在。没有它时主线程会被当成普通
    # 线程，用例就会去走补取那条路 —— 那是真的网络请求
    from PySide6.QtWidgets import QApplication

    return QApplication.instance() or QApplication([])


@pytest.fixture
def manager(app):
    # 每个用例一份独立实例：重试额度与定时器都是实例状态，共用单例会互相串
    return UserManager()


@pytest.fixture
def outbound(monkeypatch):
    # 掐掉 AsyncTask，让「有没有重新发请求」变成一次可断言的动作
    import util.auth.user as user_module

    sent = []

    monkeypatch.setattr(user_module, "AsyncTask", SimpleNamespace(run = sent.append))

    return sent


@pytest.fixture
def toasts():
    # show_toast_error 走 emit_signal，主窗口未就绪时信号会被压进待发列表而不发出去
    emitted = []

    def record(category, title, message):
        emitted.append((title, message))

    signal_bus.toast.show_long_message.connect(record)

    original = runtime.app.main_window_ready
    runtime.app.main_window_ready = True

    yield emitted

    runtime.app.main_window_ready = original

    signal_bus.toast.show_long_message.disconnect(record)


class TestEncWbi:
    @pytest.mark.parametrize("img, sub", [
        ("", ""),
        (IMG_KEY, ""),
        ("", SUB_KEY),
    ], ids = ["两个都空", "只有 img_key", "只有 sub_key"])
    def test_missing_keys_raise_readable_error(self, img, sub):
        config.set(config.img_key, img)
        config.set(config.sub_key, sub)

        with pytest.raises(RuntimeError) as excinfo:
            enc_wbi({"bvid": "BV1xx411c7mD"})

        message = str(excinfo.value)

        # 只填一个 key 同样不够：getMixinKey 要取到表里下标 62 的那一位，
        # 「拿到一个就能凑合」不成立
        assert message and "signature key" in message, (
            f"空 key 必须给出一句可读的提示，实际抛的是：{message!r}"
        )

    def test_length_boundary_is_driven_by_the_table(self):
        # 校验的是「够不够 mixinKeyEncTab 取值」，边界就取表里最大的下标，
        # 而不是「两个 key 是否各自都有 32 位」这个更容易写错的近似条件
        config.set(config.img_key, "a" * (WBI_KEY_LENGTH - 1))

        with pytest.raises(RuntimeError):
            enc_wbi({})

        config.set(config.img_key, "a" * WBI_KEY_LENGTH)

        assert "w_rid" in dict(parse_qsl(enc_wbi({})))

    def test_signs_when_both_keys_present(self):
        config.set(config.img_key, IMG_KEY)
        config.set(config.sub_key, SUB_KEY)

        params = dict(parse_qsl(enc_wbi({"bvid": "BV1xx411c7mD", "cid": 456})))

        assert params["bvid"] == "BV1xx411c7mD"
        assert params["cid"] == "456"
        assert params["wts"].isdigit()
        assert re.fullmatch(r"[0-9a-f]{32}", params["w_rid"]), "w_rid 是 query 拼接 mixin_key 后的 md5"


class TestNavResponse:
    @pytest.mark.parametrize("response", [
        {"code": -412, "message": "请求被拦截", "ttl": 1},
        {"code": -101, "message": "账号未登录", "data": {"isLogin": False}},
        {"code": 0, "data": {"isLogin": False}},
        {"code": 0, "data": None},
    ], ids = ["风控 -412", "未登录 -101", "无 wbi_img", "data 为 null"])
    def test_response_without_wbi_img_is_reported(self, manager, toasts, response):
        manager.on_get_user_info_success(response)

        assert toasts, "拿不到签名密钥时必须出声，否则后续所有解析都会以越界错误失败"

        title, message = toasts[-1]

        assert title == Translator.ERROR_MESSAGES("USER_INFO_FAILED")
        assert message

        # 关键：不能把空串当成有效密钥写进去 —— 那只是把失败从启动推迟到解析时才暴露
        assert config.get(config.img_key) == ""
        assert config.get(config.sub_key) == ""

    def test_complete_response_writes_keys(self, manager, toasts):
        manager.on_get_user_info_success({
            "code": 0,
            "data": {"isLogin": False, "wbi_img": WBI_IMG},
        })

        # 未登录也要写：这两个 key 与登录态无关，匿名请求一样要签名
        assert config.get(config.img_key) == "7cd084941338484aae1ad9425b84077c"
        assert config.get(config.sub_key) == "4932caff0ff746eab6f01bf08b70ac45"

        assert not toasts, "正常响应不该弹提示"


class TestNavRetry:
    def test_network_failure_schedules_retry_silently(self, manager, toasts):
        manager.on_get_user_info_error("timed out")

        assert manager._retry_timer.isActive(), "网络类失败要排一次重试"
        assert manager._retry_timer.interval() == UserManager.RETRY_DELAYS_MS[0]
        assert not toasts, "还有重试额度时保持安静，网络差的时候弹窗会刷屏"

    def test_gives_up_after_the_budget_and_speaks_up(self, manager, toasts):
        for _ in range(len(UserManager.RETRY_DELAYS_MS)):
            manager.on_get_user_info_error("timed out")

        assert not toasts, "额度还没用完，不该打扰用户"
        assert manager._retry_index == len(UserManager.RETRY_DELAYS_MS)

        manager.on_get_user_info_error("timed out")

        assert toasts, "彻底放弃了就必须出声，否则用户不知道解析为什么全挂"
        assert manager._retry_index == len(UserManager.RETRY_DELAYS_MS), "放弃之后不该再排新的重试"

    def test_backoff_grows_with_each_attempt(self, manager):
        delays = []

        for _ in range(len(UserManager.RETRY_DELAYS_MS)):
            manager.on_get_user_info_error("timed out")
            delays.append(manager._retry_timer.interval())

        # 定频重打容易被这个接口判成风控，间隔必须逐次拉长
        assert delays == sorted(set(delays)) and len(set(delays)) == len(delays)

    def test_response_level_failure_does_not_retry(self, manager, toasts):
        # 服务端已经答复了（风控 -412 等），再打三次只会加重限流
        manager.on_get_user_info_success({"code": -412, "message": "请求被拦截"})

        assert not manager._retry_timer.isActive()
        assert toasts

    def test_external_trigger_cancels_pending_retry(self, manager, outbound):
        manager.on_get_user_info_error("timed out")

        assert manager._retry_timer.isActive()

        manager.get_user_info()

        assert not manager._retry_timer.isActive(), "手动触发不作废重试的话，两次请求会叠在一起"
        assert manager._retry_index == 0, "手动触发是一次全新的开始，额度理应从头算"
        assert len(outbound) == 1

    def test_success_resets_the_budget_and_drops_the_pending_retry(self, manager):
        manager.on_get_user_info_error("timed out")
        manager.on_get_user_info_error("timed out")

        assert manager._retry_index == 2
        assert manager._retry_timer.isActive()

        manager.on_get_user_info_success({"code": 0, "data": {"isLogin": False, "wbi_img": WBI_IMG}})

        assert manager._retry_index == 0, "拿到密钥说明链路已经通了，额度要归零"
        assert not manager._retry_timer.isActive(), "链路已通，排着的重试没有理由再发出去"

    def test_the_timer_goes_straight_to_the_request(self, manager, outbound):
        # 直接补发一次 timeout，而不是驱动事件循环：等真实延时（最短也 5 秒）会让用例变慢，
        # 而 qWait 之类的手段会连带跑起别的测试遗留在全局队列里的定时器。
        #
        # 这里盯的是定时器连到了哪个方法 —— 必须是 _request_user_info 而不是 get_user_info，
        # 后者会把额度重置回起点，于是每次重试都重新拿到全额，退避永远不会结束
        manager.on_get_user_info_error("timed out")
        manager.on_get_user_info_error("timed out")

        assert manager._retry_index == 2

        manager._retry_timer.timeout.emit()

        assert len(outbound) == 1, "定时器到点要重新发一次请求"
        assert manager._retry_index == 2, "重试本身不该动额度，否则额度永远耗不尽"

    def test_shutdown_stops_the_timer(self, manager):
        manager.on_get_user_info_error("timed out")

        manager.shutdown()

        assert not manager._retry_timer.isActive(), "退出路上再触发会在关停过程中拉起新的请求线程"


def run_off_gui_thread(func):
    """
    在普通线程里跑一次 func，返回它抛出的异常（没抛就是 None）。

    ensure_wbi_keys 只在非 GUI 线程上补取 —— 主线程就是 GUI 线程，
    要覆盖补取那一支就必须换个线程，这也是它真实运行时的位置
    """
    box = {}

    def runner():
        try:
            func()
            box["error"] = None

        except Exception as e:
            box["error"] = e

    thread = Thread(target = runner)
    thread.start()
    thread.join()

    return box["error"]


class TestLazyFetch:
    @pytest.fixture
    def fetch(self, monkeypatch):
        # 用例绝不能真的去打 nav 接口：把补取换成可控的桩，只关心「调没调、成没成」
        import util.parse.parser.base as wbi_module

        state = {"calls": 0, "succeed": False}

        def fake_fetch():
            state["calls"] += 1

            if state["succeed"]:
                config.set(config.img_key, IMG_KEY)
                config.set(config.sub_key, SUB_KEY)
                return True

            return False

        monkeypatch.setattr(wbi_module, "_fetch_wbi_keys", fake_fetch)

        return state

    def test_does_not_block_the_gui_thread(self, fetch):
        with pytest.raises(RuntimeError):
            ensure_wbi_keys()

        assert fetch["calls"] == 0, "GUI 线程上不能发同步请求：宁可报错，也不能把界面冻住"

    def test_fetches_off_the_gui_thread(self, fetch):
        fetch["succeed"] = True

        error = run_off_gui_thread(ensure_wbi_keys)

        assert error is None, f"补取成功就不该再抛错，实际抛了：{error!r}"
        assert fetch["calls"] == 1

        # 补上之后同一个线程里就能正常签名了
        assert "w_rid" in dict(parse_qsl(enc_wbi({"bvid": "BV1xx411c7mD"})))

    def test_gives_up_readably_when_the_fetch_fails(self, fetch):
        error = run_off_gui_thread(ensure_wbi_keys)

        assert isinstance(error, RuntimeError), f"补取失败要给一句能读的话，实际是 {error!r}"
        assert "signature key" in str(error)
        assert fetch["calls"] == 1

    def test_second_caller_waits_for_the_first(self, fetch):
        # 几十个解析线程同时发现密钥为空时，只该由一个真的去发请求。
        # 这里的桩是同步的，两个线程必然一前一后拿到锁；第二个应当直接看到补好的密钥
        fetch["succeed"] = True

        errors = [run_off_gui_thread(ensure_wbi_keys) for _ in range(2)]

        assert errors == [None, None]
        assert fetch["calls"] == 1, "第二个线程应当直接复用第一个补好的密钥"

    def test_already_having_keys_skips_the_fetch(self, fetch):
        config.set(config.img_key, IMG_KEY)
        config.set(config.sub_key, SUB_KEY)

        ensure_wbi_keys()

        assert fetch["calls"] == 0, "密钥齐备时不该再打接口"


class TestKeyWriteBack:
    """
    密钥的补救路径：任何一次拿到 nav 响应的机会都要顺手回写，
    这样「启动时那次请求失败」就能被之后任意一次成功的请求救回来。
    """

    @pytest.fixture
    def login(self, app):
        from util.auth.cookie_login import CookieLogin

        return CookieLogin()

    def test_written_when_cookie_login_succeeds(self, login, monkeypatch):
        monkeypatch.setattr(login, "update_cookies", lambda: None)

        login.on_verify_success({"code": 0, "data": {"isLogin": True, "wbi_img": WBI_IMG}})

        assert config.get(config.img_key) == "7cd084941338484aae1ad9425b84077c"
        assert config.get(config.sub_key) == "4932caff0ff746eab6f01bf08b70ac45"

    def test_written_even_when_the_pasted_cookie_is_invalid(self, login, monkeypatch):
        # 密钥与登录态无关，校验失败的那份响应同样带得回它们。
        # 而「启动请求失败、用户于是手动登录」正是最需要这一份的时候
        monkeypatch.setattr(login, "restore_cookies", lambda: None)
        monkeypatch.setattr(login, "on_error", lambda message: None)

        login.on_verify_success({"code": 0, "data": {"isLogin": False, "wbi_img": WBI_IMG}})

        assert config.get(config.img_key) == "7cd084941338484aae1ad9425b84077c"

    def test_response_without_wbi_img_does_not_break_the_login_flow(self, login, monkeypatch):
        # 拿不到密钥只是少了一次补救，不能因此把登录本身判成失败
        monkeypatch.setattr(login, "update_cookies", lambda: None)

        login.on_verify_success({"code": 0, "data": {"isLogin": True}})

        assert config.get(config.img_key) == ""
        assert config.get(config.sub_key) == ""
