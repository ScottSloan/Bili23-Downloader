"""
附加内容解析中播放器信息接口失败时的降级（#488）。

字幕与章节来自同一个播放器信息接口，这一步排在音视频下载完成之后。接口被风控拦下（HTTP 412）时，
异常原先会让整个任务判为下载失败，视频卡在 100% 交付不出去。这里钉住：接口失败只跳过字幕与章节，
任务照常成功；提示经过节流，同一批任务接连失败时不会刷屏。
"""

import httpx
import pytest


def risk_control_error():
    request = httpx.Request("GET", "https://api.bilibili.com/x/player/wbi/v2")

    return httpx.HTTPStatusError("412 Precondition Failed", request = request, response = httpx.Response(412, request = request))


@pytest.fixture
def worker_env(monkeypatch):
    from util.common.signal_bus import signal_bus
    from util.parse.additional import worker

    calls = {"subtitles": 0, "chapter": 0, "toast": 0}

    def fail(self):
        raise risk_control_error()

    def count(name):
        def parse(self, player_data):
            calls[name] += 1

        return parse

    def on_toast(*args):
        calls["toast"] += 1

    monkeypatch.setattr(worker.PlayerInfoParser, "get_data", fail)
    monkeypatch.setattr(worker.SubtitlesParser, "parse", count("subtitles"))
    monkeypatch.setattr(worker.ChapterParser, "parse", count("chapter"))
    # 节流状态是模块级的，每个用例从头算
    monkeypatch.setattr(worker, "_last_player_info_warning", None)

    signal_bus.toast.show.connect(on_toast)

    yield worker, calls

    signal_bus.toast.show.disconnect(on_toast)


def make_task():
    from util.common.enum import DownloadType
    from util.download.task.info import TaskInfo

    task = TaskInfo()
    task.Download.type = DownloadType.SUBTITLE | DownloadType.CHAPTER
    task.Download.merge_video_audio = True

    return task


def run_worker(worker, task):
    results = []

    parse_worker = worker.AdditionalParseWorker(task)
    parse_worker.success.connect(lambda: results.append("success"))
    parse_worker.error.connect(lambda message: results.append(f"error: {message}"))
    parse_worker.run()

    return results


def test_risk_control_does_not_fail_task(worker_env):
    worker, calls = worker_env

    assert run_worker(worker, make_task()) == ["success"]
    assert calls["subtitles"] == 0
    assert calls["chapter"] == 0
    assert calls["toast"] == 1


def test_warning_is_throttled(worker_env):
    worker, calls = worker_env

    # 同一批任务接连失败，只提示一次
    for _ in range(3):
        assert run_worker(worker, make_task()) == ["success"]

    assert calls["toast"] == 1


def test_warning_shows_again_after_interval(worker_env, monkeypatch):
    worker, calls = worker_env

    run_worker(worker, make_task())

    monkeypatch.setattr(worker, "_last_player_info_warning", worker._last_player_info_warning - worker._PLAYER_INFO_WARNING_INTERVAL)

    run_worker(worker, make_task())

    assert calls["toast"] == 2


def test_other_errors_still_fail_task(worker_env, monkeypatch):
    # 降级只针对网络与响应解析错误，代码自身的缺陷不能被吞掉
    worker, calls = worker_env

    def broken(self):
        raise KeyError("data")

    monkeypatch.setattr(worker.PlayerInfoParser, "get_data", broken)

    assert run_worker(worker, make_task())[0].startswith("error")
