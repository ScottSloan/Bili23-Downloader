"""
util/format/units.py —— 时长、文件大小、码率的展示格式化。

这些函数的输出直接出现在解析列表和下载列表里，改动会被用户一眼看到，
因此逐个边界钉死。
"""

from util.format.units import Units

import pytest


class TestEpisodeDuration:
    @pytest.mark.parametrize(
        "duration, expected",
        [
            (None, "--:--"),    # 时长未知
            (0, ""),            # 合集节点等没有时长的条目，留空而非 00:00
            (59, "00:59"),
            (60, "01:00"),
            (3599, "59:59"),    # 不足一小时不显示小时位
            (3600, "01:00:00"), # 满一小时起显示小时位
            (3661, "01:01:01"),
            (86399, "23:59:59"),
            (90061, "25:01:01"),    # 超过一天不进位成天，继续累计小时
        ],
    )
    def test_format(self, duration, expected):
        assert Units.format_episode_duration(duration) == expected

    @pytest.mark.parametrize(
        "text, expected",
        [
            ("00:59", 59),
            ("01:00:00", 3600),
            ("12", 12),         # 纯秒数
            ("1:2:3", 3723),    # 不补零的写法同样要能解析
        ],
    )
    def test_unformat(self, text, expected):
        assert Units.unformat_episode_duration(text) == expected

    @pytest.mark.parametrize("seconds", [1, 59, 60, 3600, 3661, 86399])
    def test_roundtrip(self, seconds):
        # format 与 unformat 必须互为逆运算，课程时长（"12:34" 形式）依赖这条性质
        assert Units.unformat_episode_duration(Units.format_duration(seconds)) == seconds


class TestFileSize:
    @pytest.mark.parametrize(
        "size, expected",
        [
            (0, "0.00 B"),
            (1023, "1023.00 B"),
            (1024, "1.00 KB"),      # 1024 进制
            (1536, "1.50 KB"),
            (1024 ** 2, "1.00 MB"),
            (1024 ** 4, "1.00 TB"),
        ],
    )
    def test_format(self, size, expected):
        assert Units.format_file_size(size) == expected

    def test_beyond_largest_unit(self):
        # 超出 EB 后不应抛 IndexError，而是让数值继续增长
        assert Units.format_file_size(1024 ** 7) == "1024.00 EB"


class TestBitrate:
    @pytest.mark.parametrize(
        "bitrate, expected",
        [
            (0, ""),                # 取不到码率时留空，不显示 "0.00 bps"
            (999, "999.00 bps"),
            (1000, "1.00 Kbps"),    # 码率是 1000 进制，与文件大小不同
            (1500, "1.50 Kbps"),
            (1000000, "1.00 Mbps"),
        ],
    )
    def test_format(self, bitrate, expected):
        assert Units.format_bitrate(bitrate) == expected


class TestMisc:
    def test_frame_rate(self):
        assert Units.format_frame_rate(0) == ""
        assert Units.format_frame_rate(29.97) == "30.0 fps"

    def test_speed(self):
        assert Units.format_speed(0) == ""
        assert Units.format_speed(1024 ** 2) == "1.00 MB/s"
