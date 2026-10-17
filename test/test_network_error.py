"""
解析失败时的网络错误分类（util/network/error.py）与对应的提示对话框。

最常见的坑：程序默认跟随系统代理，代理软件退出后系统代理设置却还留着，
所有请求都撞上一个没人监听的本地端口，报「由于目标计算机积极拒绝，无法连接」。
这句话原样弹给用户毫无指向性，所以要先认出它是网络问题、再认出代理牵涉其中。

分类错了不会有任何报错，只会退回成那条看不懂的「解析失败」通知，这里逐条钉住：

1. 连接层面的失败才算网络问题，HTTP 状态码错误、连接池排队超时都不算；
2. 解析器把底层异常包一层再抛时，仍然要沿异常链认出来；
3. 是否「走了代理」以建 client 那一刻实际生效的挂载为准，展示的代理地址不能带出账号密码。
"""

from PySide6.QtWidgets import QApplication, QWidget, QLabel

import httpx
import pytest

from util.network import error as network_error
from util.network import request
from util.network.error import NetworkErrorInfo, NetworkErrorKind, classify_network_error
from util.common.enum import ProxyMode


@pytest.fixture
def no_proxy(monkeypatch):
    monkeypatch.setattr(request, "_client_proxy", None)


@pytest.fixture
def system_proxy(monkeypatch):
    monkeypatch.setattr(request, "_client_proxy", (ProxyMode.SYSTEM, "127.0.0.1:7890"))


def connect_refused():
    return httpx.ConnectError("[WinError 10061] 由于目标计算机积极拒绝，无法连接。")


class TestClassify:
    def test_connect_error_through_proxy_blames_the_proxy(self, system_proxy):
        info = classify_network_error(connect_refused())

        assert info == NetworkErrorInfo(NetworkErrorKind.PROXY, ProxyMode.SYSTEM, "127.0.0.1:7890")

    def test_connect_error_without_proxy_is_a_connection_problem(self, no_proxy):
        assert classify_network_error(connect_refused()) == NetworkErrorInfo(NetworkErrorKind.CONNECTION)

    @pytest.mark.parametrize("exc", [
        httpx.ConnectTimeout("timed out"),
        httpx.ReadTimeout("timed out"),
        httpx.ReadError("reset"),
        httpx.ProxyError("502 Bad Gateway"),
        httpx.RemoteProtocolError("Server disconnected without sending a response."),
    ])
    def test_other_connection_level_errors(self, no_proxy, exc):
        assert classify_network_error(exc) is not None

    @pytest.mark.parametrize("exc", [
        ValueError("Invalid link format"),
        RuntimeError("啥都木有"),
        # 连接池排队超时是本进程的问题，与网络、代理无关
        httpx.PoolTimeout("pool"),
        # 拿到了状态码说明连接是通的，风控 412 之类不该被说成网络问题
        httpx.HTTPStatusError(
            "412",
            request = httpx.Request("GET", "https://api.bilibili.com"),
            response = httpx.Response(412)
        ),
    ])
    def test_non_network_errors_are_left_alone(self, system_proxy, exc):
        assert classify_network_error(exc) is None

    def test_explicitly_chained_error(self, system_proxy):
        try:
            try:
                raise connect_refused()

            except httpx.ConnectError as e:
                raise RuntimeError("解析失败") from e

        except RuntimeError as e:
            assert classify_network_error(e).kind == NetworkErrorKind.PROXY

    def test_implicitly_chained_error(self, system_proxy):
        # 例如 ParserBase.check_response 在 except 块里抛出的 RuntimeError
        try:
            try:
                raise connect_refused()

            except httpx.ConnectError:
                raise RuntimeError("解析失败")

        except RuntimeError as e:
            assert classify_network_error(e).kind == NetworkErrorKind.PROXY

    def test_cyclic_chain_terminates(self, system_proxy):
        a = RuntimeError("a")
        b = RuntimeError("b")
        a.__context__ = b
        b.__context__ = a

        assert classify_network_error(a) is None


class TestResolveClientProxy:
    @pytest.fixture
    def proxy_mode(self, monkeypatch):
        from util.common.config import config

        def set_mode(mode):
            real_get = config.get

            monkeypatch.setattr(config, "get", lambda item: mode if item is config.proxy_mode else real_get(item))

        return set_mode

    def test_system_proxy_address_drops_credentials(self, proxy_mode, monkeypatch):
        proxy_mode(ProxyMode.SYSTEM)
        monkeypatch.setattr(request, "_get_environment_proxies", lambda: {"https://": "http://user:secret@127.0.0.1:7890"})

        assert request._resolve_client_proxy({"https://": object()}) == (ProxyMode.SYSTEM, "127.0.0.1:7890")

    def test_system_mode_without_system_proxy_is_direct(self, proxy_mode):
        # 选了「使用系统代理」但系统里没开代理，get_env_mounts 返回 None，请求其实是直连
        proxy_mode(ProxyMode.SYSTEM)

        assert request._resolve_client_proxy(None) is None

    def test_skipped_mount_is_direct(self, proxy_mode, monkeypatch):
        # socks4 之类 httpx 不认识的协议会被 get_env_mounts 跳过，该地址退化为直连
        proxy_mode(ProxyMode.SYSTEM)
        monkeypatch.setattr(request, "_get_environment_proxies", lambda: {"https://": "socks4://127.0.0.1:1080", "all://*.local": None})

        assert request._resolve_client_proxy({"all://*.local": None}) is None

    def test_manual_proxy(self, proxy_mode, monkeypatch):
        from util.network.proxy import Proxy

        proxy_mode(ProxyMode.MANUAL)
        monkeypatch.setattr(Proxy, "get_proxies", lambda self: {"http": "http://10.0.0.2:8080", "https": "http://10.0.0.2:8080"})

        assert request._resolve_client_proxy({"https://": object()}) == (ProxyMode.MANUAL, "10.0.0.2:8080")


class TestParseWorker:
    def run_worker(self, monkeypatch, exc, slot = None):
        from util.parse.worker import ParseWorker

        worker = ParseWorker("https://www.bilibili.com/video/BV1xx411c7mD")

        def fail(url):
            raise exc

        monkeypatch.setattr(worker, "get_parser_type", fail)

        emitted = []
        # 直连到普通函数，在当前线程就地执行，不需要事件循环
        worker.error.connect(slot or (lambda message, info: emitted.append((message, info))))
        worker.run()

        return emitted

    def test_network_error_carries_classification(self, monkeypatch, system_proxy):
        emitted = self.run_worker(monkeypatch, connect_refused())

        assert len(emitted) == 1
        assert "10061" in emitted[0][0]
        assert emitted[0][1].kind == NetworkErrorKind.PROXY

    def test_other_errors_carry_none(self, monkeypatch, system_proxy):
        emitted = self.run_worker(monkeypatch, ValueError("Invalid link format"))

        assert emitted == [("Invalid link format", None)]

    def test_classifier_failure_does_not_swallow_the_error(self, monkeypatch):
        def broken(exc):
            raise AssertionError("boom")

        monkeypatch.setattr(network_error, "classify_network_error", broken)

        emitted = self.run_worker(monkeypatch, connect_refused())

        assert len(emitted) == 1
        assert emitted[0][1] is None

    def test_single_argument_slot_still_works(self, monkeypatch, no_proxy):
        """MCP 的 parse_url 只接错误信息一个参数，信号加参数后不能把它连断"""
        messages = []

        def on_error(message):
            messages.append(message)

        self.run_worker(monkeypatch, connect_refused(), slot = on_error)

        assert len(messages) == 1


class TestDialog:
    @pytest.fixture
    def parent(self):
        if QApplication.instance() is None:
            QApplication([])

        import res.resources_rc   # noqa: F401  图标与样式表由此注册，构造控件时会用到

        return QWidget()

    def labels(self, dialog):
        return [lab.text() for lab in dialog.findChildren(QLabel)]

    @pytest.mark.parametrize("info", [
        NetworkErrorInfo(NetworkErrorKind.PROXY, ProxyMode.SYSTEM, "127.0.0.1:7890"),
        NetworkErrorInfo(NetworkErrorKind.PROXY, ProxyMode.MANUAL, "10.0.0.2:8080"),
        NetworkErrorInfo(NetworkErrorKind.PROXY, ProxyMode.SYSTEM, ""),
        NetworkErrorInfo(NetworkErrorKind.CONNECTION),
    ])
    def test_constructs(self, parent, info):
        from gui.dialog.misc.network_error import NetworkErrorDialog

        dialog = NetworkErrorDialog(info, "[WinError 10061]", parent)
        text = "\n".join(self.labels(dialog))

        # 原始报错要留在对话框里，用户反馈问题时要用
        assert "[WinError 10061]" in text

        if info.proxy_address:
            assert info.proxy_address in text
