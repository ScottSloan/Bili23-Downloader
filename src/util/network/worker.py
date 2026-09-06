"""
把一次网络请求包成 Qt worker

**这个模块只属于桌面侧。** 它是 `SyncNetWorkRequest` 的一层薄壳，把阻塞的 `run()` 结果
转成 `success` / `error` / `finished` 三个 Qt 信号，配合 `AsyncTask.run()` 使用。

之所以从 `request.py` 里拆出来，是因为那里的 `SyncNetWorkRequest` 有 **62 处**调用方
（几乎整条解析链），而 worker 只有 9 处。把 Qt 依赖留在 request.py 会让那 62 处
连带无法在 WebUI 的进程里使用 —— 而它们本来是干净的阻塞调用，`asyncio.to_thread`
直接就能用。

服务端侧不要用这个类：Qt 信号的跨线程投递需要 Qt 事件循环，而 WebUI 跑的是 asyncio（D16）。
那边直接 `await asyncio.to_thread(SyncNetWorkRequest(...).run)` 即可。
"""

from PySide6.QtCore import Signal, QObject, Slot

from .request import SyncNetWorkRequest, RequestType, ResponseType

class NetworkRequestWorker(SyncNetWorkRequest, QObject):
    success = Signal(object)
    error = Signal(str)
    finished = Signal()

    def __init__(self, url: str, request_type: RequestType = RequestType.GET, params: dict = None, response_type: ResponseType = ResponseType.JSON, raise_for_status: bool = True, json_data: dict = None, data: dict = None, content_type: str = None, extra_headers: dict = None):
        SyncNetWorkRequest.__init__(self, url, request_type, params, response_type, raise_for_status, json_data, data, content_type, extra_headers)
        QObject.__init__(self)

    @Slot()
    def run(self):
        try:
            resp = super().run()

            self.success.emit(resp)

        except Exception as e:
            self.error.emit(str(e))

        finally:
            self.proxies = None

            self.finished.emit()

    def set_proxies(self, proxies: dict):
        self.proxies = proxies
