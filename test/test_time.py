"""
util/format/time.py —— 时间戳与字幕时间轴格式化。

注意：Time.from_timestamp 返回的是**本机时区的 naive datetime**，
因此这里不断言任何绝对日期字符串 —— 那样的断言在 CI（UTC）与开发机（UTC+8）
上会得出不同结果。只钉住与时区无关的性质：毫秒归一化、往返一致性，
以及纯算术的字幕时间轴格式化。
"""

from util.format.time import Time

from datetime import datetime
import pytest


class TestTimestamp:
    def test_millisecond_normalization(self):
        # B 站部分接口返回毫秒级时间戳，阈值 1e10 以上一律按毫秒处理。
        # 归一化若失效，文件名里的 {pub_time} 会变成五位数年份
        assert Time.from_timestamp(1772841600000) == Time.from_timestamp(1772841600)

    def test_second_timestamp_below_threshold(self):
        # 1e10 秒 ≈ 公元 2286 年，低于阈值的一律按秒处理
        assert Time.from_timestamp(9_999_999_999).year > 2200

    def test_roundtrip(self):
        assert Time.to_timestamp(Time.from_timestamp(1772841600)) == 1772841600

    def test_negative_timestamp(self):
        # 1970 年之前的时间戳不应抛异常（Windows 上 datetime.fromtimestamp 会报错，
        # 由 _EPOCH + timedelta 兜底）
        assert Time.from_timestamp(-1).year == 1969

    def test_out_of_range_timestamp(self):
        # 远超 datetime 支持范围的脏数据同样不能让格式化崩掉
        assert Time.from_timestamp(99_999_999_999_999).year > 5000

    def test_string_roundtrip(self):
        text = "2026-03-07 12:34:56"
        assert Time.format_timestamp(Time.timestamp_from_string(text)) == text

    def test_to_timestamp_strips_tzinfo_on_overflow(self):
        # 带时区的 datetime 走兜底分支时需要先剥掉 tzinfo，否则相减会抛 TypeError
        assert isinstance(Time.to_timestamp(datetime(2026, 3, 7)), float)


class TestSrtTime:
    @pytest.mark.parametrize(
        "seconds, expected",
        [
            (0, "00:00:00,000"),
            (3661.5, "01:01:01,500"),
            (59.9999, "00:01:00,000"),  # 毫秒四舍五入到 1000 时必须向上进位，不能留下 ",1000"
        ],
    )
    def test_format(self, seconds, expected):
        assert Time.format_srt_time(seconds) == expected


class TestAssTime:
    @pytest.mark.parametrize(
        "ms, expected",
        [
            (0, "0:00:00.00"),
            (3661999, "1:01:01.99"),    # 厘秒进位到 100 时钳到 99，ASS 不接受 .100
        ],
    )
    def test_format_by_ms(self, ms, expected):
        assert Time.format_ass_time_by_ms(ms) == expected

    @pytest.mark.parametrize(
        "seconds, expected",
        [
            (0, "0:00:00.00"),
            (59.999, "0:01:00.00"),     # 与 by_ms 不同，这里走的是逐级进位
            (3661.5, "1:01:01.50"),
        ],
    )
    def test_format_by_seconds(self, seconds, expected):
        assert Time.format_ass_time_by_seconds(seconds) == expected
