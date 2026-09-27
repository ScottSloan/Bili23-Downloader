"""
解析界面的 wbi 签名前置闸门（gui/interface/parse.py）。

密钥没就绪时直接发起解析必然失败，用户看到的是「解析失败」，会当成程序坏了 ——
而这其实只是密钥还没到。这里改成先等密钥到位再自动继续。

用例盯的是状态机的那几条分支：等待 / 到位后继续 / 超时 / 手动放弃 /
不需要签名的类型不受影响 / 等待期间重复触发不叠成两次解析。
"""

import pytest

from util.common.config import config
from util.common.runtime import runtime
from util.common.signal_bus import signal_bus
from util.common.translator import Translator


VIDEO_URL = "https://www.bilibili.com/video/BV1xx411c7mD"
BANGUMI_URL = "https://www.bilibili.com/bangumi/play/ss12345"

IMG_KEY = "a" * 32
SUB_KEY = "b" * 32


@pytest.fixture(autouse = True)
def clean_keys():
    config.set(config.img_key, "")
    config.set(config.sub_key, "")

    yield

    config.set(config.img_key, "")
    config.set(config.sub_key, "")


@pytest.fixture(autouse = True)
def app():
    from PySide6.QtWidgets import QApplication

    instance = QApplication.instance() or QApplication([])

    import res.resources_rc     # noqa: F401  图标由它注册，构造界面时要用

    return instance


@pytest.fixture(autouse = True)
def kicks(monkeypatch):
    """
    等待期间会往全局线程池里推补取任务。这里让它就地同步跑完，并把真正的补取换掉 ——
    用例绝不能去打 nav 接口。返回值记录补取被推了几次
    """
    import gui.interface.parse as parse_module

    calls = []

    monkeypatch.setattr(parse_module, "ensure_wbi_keys", lambda: calls.append(1))
    monkeypatch.setattr(parse_module.GlobalThreadPoolTask, "run_func", staticmethod(lambda func, *args, **kwargs: func()))

    return calls


@pytest.fixture
def started(monkeypatch):
    """挡住真正的解析，只记录「有没有发起、发起了几次」"""
    from gui.interface.parse import ParseInterface

    recorded = []
    monkeypatch.setattr(ParseInterface, "start_parse", lambda self, worker: recorded.append(worker))

    return recorded


@pytest.fixture
def interface(app):
    from gui.interface.parse import ParseInterface

    return ParseInterface()


@pytest.fixture
def toasts():
    emitted = []

    def record(category, title, message):
        emitted.append((title, message))

    signal_bus.toast.show.connect(record)

    original = runtime.app.main_window_ready
    runtime.app.main_window_ready = True

    yield emitted

    runtime.app.main_window_ready = original

    signal_bus.toast.show.disconnect(record)


def give_keys():
    config.set(config.img_key, IMG_KEY)
    config.set(config.sub_key, SUB_KEY)


class TestGate:
    def test_ready_keys_parse_immediately(self, interface, started):
        give_keys()

        interface.url_box.setText(VIDEO_URL)
        interface.on_parse()

        assert len(started) == 1
        assert not interface._wbi_wait_timer.isActive()

    def test_wbi_type_waits_instead_of_parsing(self, interface, started, kicks, toasts):
        interface.url_box.setText(VIDEO_URL)
        interface.on_parse()

        assert not started, "密钥没就绪时不该发起一次注定失败的解析"
        assert interface._wbi_wait_timer.isActive()
        assert kicks, "等待不能是干等，要推一把补取"
        assert not toasts, "等待期间不该弹任何错误"
        assert interface.progress_widget.tip_lab.text() == Translator.TIP_MESSAGES("WBI_KEY_WAITING")

    def test_type_without_wbi_is_not_gated(self, interface, started):
        interface.url_box.setText(BANGUMI_URL)
        interface.on_parse()

        assert len(started) == 1, "番剧打的是不需要签名的接口，不该被拦下"
        assert not interface._wbi_wait_timer.isActive()

    def test_resumes_once_the_keys_arrive(self, interface, started):
        interface.url_box.setText(VIDEO_URL)
        interface.on_parse()

        assert not started

        give_keys()

        interface._on_wbi_wait_tick()

        assert len(started) == 1, "密钥到位后要自动接着解析，不该让用户再点一次"
        assert not interface._wbi_wait_timer.isActive()
        assert interface._pending_parse_worker is None

    def test_times_out_with_a_network_flavoured_message(self, interface, started, toasts):
        interface.url_box.setText(VIDEO_URL)
        interface.on_parse()

        interface._wbi_wait_deadline = 0.0    # 直接推到超时之后，不必真等 65 秒
        interface._on_wbi_wait_tick()

        assert not started, "超时也不能硬发一次注定失败的解析"
        assert not interface._wbi_wait_timer.isActive()

        title, message = toasts[-1]

        assert title == Translator.ERROR_MESSAGES("WBI_KEY_UNAVAILABLE_TITLE"), "问题在网络侧，标题不该说「解析失败」"
        assert "signature key" in message

    def test_stop_button_leaves_the_wait(self, interface, started):
        interface.url_box.setText(VIDEO_URL)
        interface.on_parse()

        interface.cancel_wbi_wait()

        assert not interface._wbi_wait_timer.isActive()
        assert not started
        assert interface._pending_parse_worker is None

    def test_repeated_triggers_do_not_stack(self, interface, started):
        interface.url_box.setText(VIDEO_URL)

        interface.on_parse()
        interface.on_parse()        # 回车再敲一次
        interface.on_parse(2)       # 翻页

        give_keys()

        interface._on_wbi_wait_tick()

        assert len(started) == 1, "等待期间重复触发不该排成多次解析"

    def test_invalid_link_falls_through_to_the_worker(self, interface, started):
        # 链接不合法时不能在 GUI 线程里抛 ValueError：交给 worker 走既有的提示路径
        interface.url_box.setText("这不是一条链接")

        interface.on_parse()

        assert len(started) == 1
        assert not interface._wbi_wait_timer.isActive()
