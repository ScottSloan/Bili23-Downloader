"""Independent, bounded media inspection. No Qt or user configuration imports."""
from dataclasses import asdict, dataclass, field
from pathlib import Path
from threading import Event
import json
import math
import os
import shutil
import subprocess
import tempfile
import time


@dataclass
class ProbeResult:
    status: str = "unverified"
    reason: str = ""
    duration: float | None = None
    format_name: str = ""
    streams: list[dict] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)

    def to_dict(self):
        return asdict(self)


def find_ffprobe(ffmpeg_path: str | None = None) -> str | None:
    """Prefer the configured FFmpeg's sibling, then PATH; never download tools."""
    name = "ffprobe.exe" if os.name == "nt" else "ffprobe"
    if ffmpeg_path:
        sibling = Path(ffmpeg_path).absolute().with_name(name)
        if sibling.is_file() and os.access(sibling, os.X_OK):
            return str(sibling)
    return shutil.which(name)


def _positive(value, convert=float):
    try:
        number = convert(value)
        return number if math.isfinite(number) and number > 0 else None
    except (TypeError, ValueError, OverflowError):
        return None


def parse_probe(data: dict, *, expect_video=False, expect_audio=False,
                expected_duration: float | None = None) -> ProbeResult:
    if not isinstance(data, dict) or not isinstance(data.get("streams"), list):
        return ProbeResult(status="failed", reason="invalid_probe_output")
    result = ProbeResult(status="verified")
    media_format = data.get("format", {})
    if not isinstance(media_format, dict):
        return ProbeResult(status="failed", reason="invalid_probe_output")
    result.format_name = str(media_format.get("format_name", ""))
    result.duration = _positive(media_format.get("duration"))
    for stream in data["streams"]:
        if not isinstance(stream, dict):
            return ProbeResult(status="failed", reason="invalid_probe_output")
        if stream.get("codec_type") not in ("video", "audio"):
            continue
        # Embedded cover art is not a playable video track.
        disposition = stream.get("disposition") or {}
        if stream.get("codec_type") == "video" and disposition.get("attached_pic"):
            continue
        result.streams.append({
            "type": stream["codec_type"], "codec": stream.get("codec_name"),
            "width": _positive(stream.get("width"), int),
            "height": _positive(stream.get("height"), int),
            "sample_rate": _positive(stream.get("sample_rate"), int),
            "channels": _positive(stream.get("channels"), int),
            "bit_rate": _positive(stream.get("bit_rate"), int),
        })
    types = {s["type"] for s in result.streams}
    if not types or (expect_video and "video" not in types) or (expect_audio and "audio" not in types):
        result.status, result.reason = "failed", "missing_required_stream"
    expected = _positive(expected_duration)
    if expected and result.duration and abs(expected - result.duration) > max(2.0, expected * 0.01):
        result.warnings.append("duration_mismatch")
    if result.status == "verified" and result.warnings:
        result.status = "warning"
    return result


def probe_media(path: str | Path, *, executable: str | None = None,
                timeout: float = 15, cancel: Event | None = None, **expectations) -> ProbeResult:
    """Quick structural check, not a full decode. Output and runtime are bounded."""
    if not math.isfinite(timeout) or timeout <= 0:
        raise ValueError("timeout must be positive and finite")
    if cancel and cancel.is_set():
        return ProbeResult(reason="cancelled")
    if not Path(path).is_file():
        return ProbeResult(status="failed", reason="file_missing")
    executable = executable or find_ffprobe()
    if not executable:
        return ProbeResult(reason="ffprobe_missing")
    command = [executable, "-v", "error", "-show_entries",
               "format=format_name,duration:stream=codec_type,codec_name,width,height,sample_rate,channels,bit_rate:stream_disposition=attached_pic",
               "-of", "json", "-i", str(Path(path).absolute())]
    # Temporary files avoid PIPE deadlocks and unbounded in-memory communicate().
    # Poll file sizes and terminate tools emitting excessive output.
    with tempfile.TemporaryFile() as stdout, tempfile.TemporaryFile() as stderr:
        try:
            proc = subprocess.Popen(command, stdout=stdout, stderr=stderr,
                                    creationflags=subprocess.CREATE_NO_WINDOW if os.name == "nt" else 0)
        except OSError:
            return ProbeResult(reason="ffprobe_unavailable")
        deadline = time.monotonic() + timeout
        reason = ""
        try:
            while proc.poll() is None:
                if cancel and cancel.is_set():
                    reason = "cancelled"
                elif time.monotonic() >= deadline:
                    reason = "timeout"
                elif max(os.fstat(stdout.fileno()).st_size, os.fstat(stderr.fileno()).st_size) > 1024 * 1024:
                    reason = "output_limit"
                if reason:
                    return ProbeResult(reason=reason)
                time.sleep(0.02)
        finally:
            if proc.poll() is None:
                proc.kill()
            proc.wait()
        if proc.returncode:
            return ProbeResult(status="failed", reason="probe_failed")
        stdout.seek(0)
        raw = stdout.read(1024 * 1024 + 1)
        if len(raw) > 1024 * 1024:
            return ProbeResult(reason="output_limit")
        try:
            return parse_probe(json.loads(raw), **expectations)
        except (ValueError, TypeError, AttributeError):
            return ProbeResult(status="failed", reason="invalid_probe_output")
