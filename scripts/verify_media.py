#!/usr/bin/env python3
"""Inspect a downloaded file without starting the GUI or accessing account data."""
import argparse
import json
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))

from util.media_probe import find_ffprobe, probe_media  # noqa: E402


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("file", type=Path)
    parser.add_argument("--ffprobe", help="Path to ffprobe executable")
    parser.add_argument("--expect-video", action="store_true")
    parser.add_argument("--expect-audio", action="store_true")
    parser.add_argument("--expected-duration", type=float, help="Expected duration in seconds")
    args = parser.parse_args()
    bundled = Path(__file__).resolve().parents[1] / "bundle" / "ffmpeg"
    result = probe_media(args.file, executable=args.ffprobe or find_ffprobe(str(bundled)),
                         expect_video=args.expect_video, expect_audio=args.expect_audio,
                         expected_duration=args.expected_duration)
    print(json.dumps(result.to_dict(), ensure_ascii=False, indent=2))
    return {"verified": 0, "warning": 0, "unverified": 2, "failed": 1}[result.status]


if __name__ == "__main__":
    sys.exit(main())
