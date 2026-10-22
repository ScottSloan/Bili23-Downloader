"""
下载数据的完整性校验（Issue #449）。

上一次修复保证了「每个分片都写满」，但用户随后给出的逐块对比显示，损坏区域无一例外是
从某个分片中间的续传点一直坏到分片末尾，或者整片都坏 —— 节点对 Range 请求回了 206、
给的却不是所请求的那一段，程序照单全收写进了文件。

这里用 httpx.MockTransport 扮演行为异常的节点，直接驱动 ChunkWorker 的下载循环，
断言的是落盘字节本身，而不是计数器：

1. 节点给错区间、给的是另一个版本的文件时，一个字节都不能写进去；
2. 正常节点续传之后，文件必须与源数据逐字节一致；
3. 节点给了 MD5 时，文件完成后要整体比对，不过就整个重下，且重下次数有上限；
4. 重新解析发现远端文件变了，旧进度必须作废。
"""

from PySide6.QtWidgets import QApplication

from threading import Event, Lock
import hashlib
import httpx
import pytest


FILE_SIZE = 64 * 1024
CHUNK_RANGE = (16 * 1024, 48 * 1024)
SOURCE = bytes((i * 7 + 13) % 251 for i in range(FILE_SIZE))
SOURCE_MD5 = hashlib.md5(SOURCE).hexdigest()
URL = "https://upos-sz-mirrorcos.bilivideo.com/upgcxcode/test.m4s"


@pytest.fixture(scope = "module")
def app():
    return QApplication.instance() or QApplication([])


@pytest.fixture(autouse = True)
def isolate_host_health():
    # 给错数据的节点会被记入跨任务共享的健康状态，不能漏到别的用例里
    from util.network.cdn import HostHealth

    with HostHealth._lock:
        saved = (dict(HostHealth._failures), dict(HostHealth._cooldown_until))

        HostHealth._failures.clear()
        HostHealth._cooldown_until.clear()

    yield HostHealth

    with HostHealth._lock:
        HostHealth._failures.clear()
        HostHealth._failures.update(saved[0])
        HostHealth._cooldown_until.clear()
        HostHealth._cooldown_until.update(saved[1])


class _BrokenStream(httpx.SyncByteStream):
    # 给出一段数据后连接断开，模拟 CDN 中途掐断
    def __init__(self, data: bytes):
        self.data = data

    def __iter__(self):
        yield self.data

        raise httpx.ReadError("peer closed connection")


def _parse_range(request: httpx.Request):
    start, _, end = request.headers["Range"].removeprefix("bytes=").partition("-")

    return int(start), int(end)


def _good(request, etag = SOURCE_MD5, total = FILE_SIZE):
    start, end = _parse_range(request)

    headers = {"Content-Range": f"bytes {start}-{end}/{total}"}

    if etag:
        headers["ETag"] = f'"{etag}"'

    return httpx.Response(206, headers = headers, content = SOURCE[start:end + 1])


def _ignore_resume_start(request):
    # 无视续传起点，从分片开头给起。Content-Range 照实标的是它给的区间
    _, end = _parse_range(request)
    start = CHUNK_RANGE[0]

    return httpx.Response(206, headers = {"Content-Range": f"bytes {start}-{end}/{FILE_SIZE}"}, content = SOURCE[start:end + 1])


def _drop_after(request, size):
    start, end = _parse_range(request)

    return httpx.Response(
        206,
        headers = {"Content-Range": f"bytes {start}-{end}/{FILE_SIZE}", "Content-Length": str(end + 1 - start)},
        stream = _BrokenStream(SOURCE[start:start + size])
    )


class _Parent:
    def is_generation_active(self, generation):
        return True


def _run_chunk(tmp_path, monkeypatch, responses, md5 = ""):
    from util.download.downloader.downloader import ChunkWorker
    from util.download.task.info import TaskInfo

    path = tmp_path / "video.m4s"
    path.write_bytes(b"\0" * FILE_SIZE)

    task_info = TaskInfo()
    task_info.Download.files = {
        "video": {
            "chunks_list": [0],
            "total_chunks": 1,
            "finished_chunks": 0,
            "chunk_offsets": {"0": 0},
            "file_size": FILE_SIZE,
            "md5": md5,
            "md5_failures": 0
        }
    }

    queue = list(responses)
    requests = []

    def handler(request):
        requests.append(request)

        return queue.pop(0)(request) if len(queue) > 1 else queue[0](request)

    session = httpx.Client(transport = httpx.MockTransport(handler))

    worker = ChunkWorker(
        session = session,
        file_key = "video",
        chunk_index = 0,
        chunk_range = CHUNK_RANGE,
        file_path = path,
        url = URL,
        referer = "",
        task_info = task_info,
        stop_event = Event(),
        lock = Lock(),
        token_bucket = None,
        generation = 0,
        parent = _Parent(),
        file_size = FILE_SIZE
    )

    outcome = {"finished": False, "errors": []}

    monkeypatch.setattr(worker, "_notify_chunk_finished", lambda: outcome.update(finished = True))
    monkeypatch.setattr(worker, "_invoke_download_error", lambda message, retryable: outcome["errors"].append((message, retryable)))
    monkeypatch.setattr(worker, "_interruptible_sleep", lambda seconds: None)

    try:
        worker._download_chunk()

    finally:
        session.close()

    return path.read_bytes(), task_info, outcome, requests


def _chunk(data: bytes):
    return data[CHUNK_RANGE[0]:CHUNK_RANGE[1]]


class TestParsing:
    def test_content_range(self):
        from util.download.downloader.integrity import parse_content_range

        assert parse_content_range("bytes 0-99/1000") == (0, 99, 1000)
        assert parse_content_range("bytes 5-9/*") == (5, 9, None)
        assert parse_content_range("BYTES 1-2/3") == (1, 2, 3)

        for value in (None, "", "bytes */1000", "bytes 0-99", "items 0-1/2"):
            assert parse_content_range(value) is None

    def test_etag(self):
        from util.download.downloader.integrity import normalize_etag, is_md5

        # 阿里云节点给的是大写，其余是小写，必须视为同一个值
        assert normalize_etag('"C3925ABF0154D98095B824A712641D23"') == "c3925abf0154d98095b824a712641d23"
        assert normalize_etag('W/"abc"') == "abc"
        assert normalize_etag(None) == ""

        assert is_md5("c3925abf0154d98095b824a712641d23")
        # nginx 风格的「修改时间-长度」换个节点就变，不能拿来比对内容
        assert not is_md5("5f1a2b3c-11cf3b")
        assert not is_md5("")

    def test_file_md5(self, tmp_path):
        from util.download.downloader.integrity import file_md5

        path = tmp_path / "data.bin"
        path.write_bytes(SOURCE)

        assert file_md5(path, block_size = 1000) == SOURCE_MD5

        stop = Event()
        stop.set()

        assert file_md5(path, stop) is None


class TestChunkResponseValidation:
    def test_resume_from_wrong_offset_is_rejected(self, tmp_path, monkeypatch, isolate_host_health):
        # 复现用户报告的形状：首轮下了一段后断开，续传时节点无视起点从分片开头给起。
        # 原先这段字节会被写到续传点上，从那里一直错到分片末尾
        data, _, outcome, requests = _run_chunk(tmp_path, monkeypatch, [
            lambda request: _drop_after(request, 8192),
            _ignore_resume_start,
            _good
        ])

        assert _chunk(data) == _chunk(SOURCE)
        assert outcome["finished"]
        assert not outcome["errors"]
        assert len(requests) == 3
        # 给错数据的节点要记入健康状态，任务级重试重新解析时才会避开它
        assert isolate_host_health._failures.get("upos-sz-mirrorcos.bilivideo.com") == 1

    def test_other_version_of_file_is_rejected(self, tmp_path, monkeypatch):
        # 区间对得上但文件总长不同：节点上是另一个版本的文件，一个字节都不能写
        data, _, outcome, _ = _run_chunk(tmp_path, monkeypatch, [
            lambda request: _good(request, total = FILE_SIZE + 1)
        ])

        assert data == b"\0" * FILE_SIZE
        assert not outcome["finished"]
        assert len(outcome["errors"]) == 1
        # 节点问题属于网络类错误，要交给任务级自动重试
        assert outcome["errors"][0][1] is True

    def test_missing_content_range_is_rejected(self, tmp_path, monkeypatch):
        def no_range(request):
            start, end = _parse_range(request)

            return httpx.Response(206, content = SOURCE[start:end + 1])

        data, _, outcome, _ = _run_chunk(tmp_path, monkeypatch, [no_range])

        assert data == b"\0" * FILE_SIZE
        assert not outcome["finished"]

    def test_md5_etag_is_recorded(self, tmp_path, monkeypatch):
        data, task_info, outcome, _ = _run_chunk(tmp_path, monkeypatch, [_good])

        assert _chunk(data) == _chunk(SOURCE)
        assert outcome["finished"]
        assert task_info.Download.files["video"]["md5"] == SOURCE_MD5

    def test_etag_mismatch_is_rejected(self, tmp_path, monkeypatch):
        other = "0" * 32

        data, _, outcome, _ = _run_chunk(tmp_path, monkeypatch, [
            lambda request: _good(request, etag = other),
            _good
        ], md5 = SOURCE_MD5)

        assert _chunk(data) == _chunk(SOURCE)
        assert outcome["finished"]

    def test_non_md5_etag_is_ignored(self, tmp_path, monkeypatch):
        # PCDN / nginx 风格的 ETag 不参与判定，否则换个节点就会被误判
        data, task_info, outcome, _ = _run_chunk(tmp_path, monkeypatch, [
            lambda request: _good(request, etag = "5f1a2b3c-11cf3b")
        ], md5 = SOURCE_MD5)

        assert _chunk(data) == _chunk(SOURCE)
        assert outcome["finished"]
        assert task_info.Download.files["video"]["md5"] == SOURCE_MD5


@pytest.fixture
def downloader(app, monkeypatch):
    from util.download.downloader.downloader import Downloader
    from util.download.task.info import TaskInfo
    from util.common.enum import DownloadStatus

    task_info = TaskInfo()
    task_info.Basic.task_id = "integrity-test"
    task_info.Download.status = DownloadStatus.DOWNLOADING
    task_info.Download.queue = ["video"]
    task_info.Download.total_size = FILE_SIZE
    task_info.Download.progress = 100
    task_info.Download.downloaded_size = FILE_SIZE
    task_info.Download.files = {
        "video": {
            "chunks_list": [],
            "total_chunks": 1,
            "finished_chunks": 1,
            "chunk_offsets": {"0": FILE_SIZE},
            "file_size": FILE_SIZE,
            "md5": SOURCE_MD5,
            "md5_failures": 0
        }
    }

    instance = Downloader(task_info)
    instance.chunk_size = FILE_SIZE
    instance.download_list = {"video": {"file_size": FILE_SIZE, "url": URL, "file_path": "unused"}}

    errors = []

    monkeypatch.setattr(instance, "update_item", lambda task_info: None)
    monkeypatch.setattr(instance, "on_download_error", lambda message, retryable: errors.append((message, retryable)))

    instance.errors = errors

    yield instance

    instance._retry_timer.stop()
    instance._close_session()


class TestFileVerification:
    def test_match_dequeues(self, downloader, monkeypatch):
        dequeued = []

        monkeypatch.setattr("util.download.downloader.downloader.task_manager.update_async", lambda task_info: dequeued.append(True))
        monkeypatch.setattr(downloader, "on_download_completed", lambda: None)

        downloader.on_md5_checked("video", SOURCE_MD5, SOURCE_MD5, downloader.download_generation)

        assert "video" in downloader._md5_verified
        assert downloader.task_info.Download.queue == []
        assert not downloader.errors

    def test_mismatch_redownloads_once_then_gives_up(self, downloader):
        file_info = downloader.task_info.Download.files["video"]

        downloader.on_md5_checked("video", SOURCE_MD5, "0" * 32, downloader.download_generation)

        # 不知道坏在哪一片，整个文件作废，进度一并归零
        assert file_info["total_chunks"] == 0
        assert file_info["chunk_offsets"] == {}
        assert file_info["md5"] == ""
        assert file_info["md5_failures"] == 1
        assert downloader.task_info.Download.downloaded_size == 0
        assert downloader.task_info.Download.progress == 0
        assert downloader.task_info.Download.queue == ["video"]
        assert downloader.errors[-1][1] is True, "首次不通过应当走自动重试"

        downloader.on_md5_checked("video", SOURCE_MD5, "0" * 32, downloader.download_generation)

        assert file_info["md5_failures"] == 2
        assert downloader.errors[-1][1] is False, "重下之后仍不通过，再重下只是浪费流量"

    def test_stale_result_is_ignored(self, downloader):
        # 校验期间被暂停过，结果作废，恢复后会重新校验
        downloader.on_md5_checked("video", SOURCE_MD5, "0" * 32, downloader.download_generation - 1)

        assert downloader.task_info.Download.files["video"]["md5_failures"] == 0
        assert not downloader.errors

    def test_full_progress_with_pending_queue_is_not_completed(self, downloader, monkeypatch):
        # 进度 100 但队列里还有文件（正在校验、或刚因校验失败被重置）时不能直接判完成，
        # 否则没校验过甚至已知是坏的文件会被送去合并
        from util.common.enum import DownloadType, DownloadStatus

        completed = []
        parse_started = []

        downloader.task_info.Download.type = DownloadType.VIDEO

        monkeypatch.setattr(downloader, "on_download_completed", lambda: completed.append(True))
        monkeypatch.setattr("util.download.downloader.downloader.GlobalThreadPoolTask.run", lambda runnable: parse_started.append(runnable))

        downloader.start()

        assert not completed
        # 改为重新解析，剩下的文件交给 start_worker 补做出队或重下
        assert parse_started
        assert downloader.task_info.Download.status == DownloadStatus.PARSING

    def test_remote_file_change_resets_progress(self, downloader):
        downloader.download_list = {"video": {"file_size": FILE_SIZE + 1}}

        downloader._sync_file_fields()

        file_info = downloader.task_info.Download.files["video"]

        assert file_info["file_size"] == FILE_SIZE + 1
        assert file_info["total_chunks"] == 0
        assert file_info["chunk_offsets"] == {}

    def test_legacy_snapshot_gets_fields(self, downloader):
        file_info = downloader.task_info.Download.files["video"]

        del file_info["md5"]
        del file_info["md5_failures"]

        downloader._sync_file_fields()

        assert file_info["md5"] == ""
        assert file_info["md5_failures"] == 0
        # 远端没变，进度保持不动
        assert file_info["total_chunks"] == 1
