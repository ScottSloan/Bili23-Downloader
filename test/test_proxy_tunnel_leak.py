"""
经 HTTP 代理时，隧道 TLS 握手超时的连接永久占住连接池（Issue #509）。

httpcore 1.0.9 在「代理已应答 CONNECT 200、随后隧道里的 TLS 握手失败」时不关闭底层连接，
连接池永远回收不了它。批量下载经本地代理跑几十分钟后，槽位被一个个泄漏光，所有请求
（含 CDN 探测）都只能 PoolTimeout，只有重启程序才能恢复。

这里用一个应答 CONNECT 后就一言不发的假代理复现：修补后每次握手超时都应当报 ConnectTimeout、
连接随即被清理；若退化成 PoolTimeout 或池中留下连接，说明补丁失效 —— 多半是 httpcore
升级改了内部实现，需要重新确认上游是否已修复。
"""

import socket
import threading

import httpx
import pytest


@pytest.fixture
def silent_tunnel_proxy():
    # 应答 CONNECT 200 之后不再发送任何数据，让隧道里的 TLS 握手撞上超时
    server = socket.socket()
    server.bind(("127.0.0.1", 0))
    server.listen(16)

    accepted = []
    stopped = threading.Event()

    def serve():
        while not stopped.is_set():
            try:
                conn, _ = server.accept()

            except OSError:
                return

            accepted.append(conn)

            try:
                conn.recv(4096)
                conn.sendall(b"HTTP/1.1 200 Connection established\r\n\r\n")

            except OSError:
                pass

    thread = threading.Thread(target = serve, daemon = True)
    thread.start()

    yield "http://127.0.0.1:{port}".format(port = server.getsockname()[1])

    stopped.set()
    server.close()
    thread.join(timeout = 5)

    for conn in accepted:
        conn.close()


def test_failed_tunnel_handshake_releases_pool_slot(silent_tunnel_proxy):
    from util.network.request import get_mounts

    # 走项目自己的挂载构造路径，补丁由它负责应用
    mounts = get_mounts({"http": silent_tunnel_proxy, "https": silent_tunnel_proxy})
    transport = mounts["https://"]

    # 池子只留 2 个槽位：修补前第 3 次请求起就全是 PoolTimeout
    transport._pool._max_connections = 2

    with httpx.Client(mounts = mounts, timeout = httpx.Timeout(0.5, pool = 0.5)) as client:
        for _ in range(4):
            with pytest.raises(httpx.ConnectTimeout):
                client.head("https://example.com/")

            assert transport._pool.connections == []

    mounts["http://"].close()


def test_patch_is_applied_once():
    from httpcore._sync.http_proxy import TunnelHTTPConnection

    from util.network.request import ensure_tunnel_connection_patched

    ensure_tunnel_connection_patched()
    patched = TunnelHTTPConnection.handle_request

    ensure_tunnel_connection_patched()

    # 重复调用不能层层包裹，否则每次创建 Client 都会多套一层
    assert TunnelHTTPConnection.handle_request is patched
    assert getattr(patched, "_bili23_tunnel_patch", False)
