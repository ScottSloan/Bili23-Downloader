import json
import subprocess
import sys
from threading import Event

from util.media_probe import parse_probe, probe_media


def test_audio_with_cover_is_not_video():
    result = parse_probe({"streams": [
        {"codec_type": "audio", "codec_name": "aac", "bit_rate": "N/A"},
        {"codec_type": "video", "disposition": {"attached_pic": 1}},
    ]}, expect_audio=True)
    assert result.status == "verified"
    assert result.streams[0]["bit_rate"] is None
    assert len(result.streams) == 1
    assert parse_probe({"streams": []}, expect_audio=True).status == "failed"


def test_duration_mismatch_and_invalid_values():
    data = {"streams": [{"codec_type": "video", "width": 1920, "height": 1080}],
            "format": {"duration": "100"}}
    assert parse_probe(data, expected_duration=200).status == "warning"
    data["format"]["duration"] = "NaN"
    assert parse_probe(data).duration is None
    assert parse_probe({"streams": [None]}).reason == "invalid_probe_output"


def test_missing_tool_file_and_cancellation(tmp_path, monkeypatch):
    path = tmp_path / "video.mp4"
    assert probe_media(path).reason == "file_missing"
    path.touch()
    monkeypatch.setattr("util.media_probe.find_ffprobe", lambda: None)
    assert probe_media(path).reason == "ffprobe_missing"
    event = Event()
    event.set()
    assert probe_media(path, cancel=event).reason == "cancelled"


def test_subprocess_success_failure_and_timeout(tmp_path, monkeypatch):
    path = tmp_path / "video.mp4"
    path.touch()
    original = subprocess.Popen
    code = "print(" + repr(json.dumps({"streams": [{"codec_type": "audio"}]})) + ")"

    def launch(command, **kwargs):
        return original([sys.executable, "-c", code], **kwargs)

    monkeypatch.setattr("util.media_probe.subprocess.Popen", launch)
    assert probe_media(path, executable="fake", expect_audio=True).status == "verified"
    code = "raise SystemExit(1)"
    assert probe_media(path, executable="fake").reason == "probe_failed"
    code = "import time; time.sleep(30)"
    assert probe_media(path, executable="fake", timeout=0.1).reason == "timeout"
    code = "print('x'*1100000)"
    assert probe_media(path, executable="fake").reason == "output_limit"


def test_cover_does_not_satisfy_required_video():
    data = {"streams": [{"codec_type": "audio"},
                        {"codec_type": "video", "disposition": {"attached_pic": 1}}]}
    assert parse_probe(data, expect_video=True).reason == "missing_required_stream"


def test_subprocess_cancel_reaps_child(tmp_path, monkeypatch):
    from threading import Timer
    path = tmp_path / "video.mp4"
    path.touch()
    original = subprocess.Popen
    children = []

    def launch(command, **kwargs):
        child = original([sys.executable, "-c", "import time; time.sleep(30)"], **kwargs)
        children.append(child)
        return child

    monkeypatch.setattr("util.media_probe.subprocess.Popen", launch)
    event = Event()
    timer = Timer(0.1, event.set)
    timer.start()
    try:
        assert probe_media(path, executable="fake", cancel=event).reason == "cancelled"
        assert children[0].poll() is not None
    finally:
        timer.join()
