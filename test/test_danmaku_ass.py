"""
util/parse/additional/file/danmaku_ass.py —— 弹幕 ASS 生成。

弹幕样式对话框里的「滚动时长」「静止时长」曾经只落盘、不生效：生成器把
时长写死成 10s / 5s，用户怎么改产物都一样，而下载流程不会有任何报错。
这里直接解析产物里每条 Dialogue 的起止时间，确认时长确实取自配置。
"""

from PySide6.QtWidgets import QApplication

from util.common.config import config
from util.parse.additional.file.danmaku_ass import DanmakuASS

import copy
import pytest


@pytest.fixture(scope = "module")
def app():
    # 布局引擎用 QFontMetrics 量文字宽度，必须先有 QApplication
    return QApplication.instance() or QApplication([])


@pytest.fixture
def durations(monkeypatch):
    # 打桩 config.get 而非 config.set 落盘，理由同 test_cdn_candidates；
    # 返回深拷贝，避免改到 DefaultValue（conftest 会在结束时校验）
    def apply(scroll: int, static: int):
        original_get = config.get

        def fake_get(item):
            if item is config.danmaku_style:
                style = copy.deepcopy(original_get(item))
                style["advanced"]["scroll_duration"] = scroll
                style["advanced"]["static_duration"] = static

                return style

            return original_get(item)

        monkeypatch.setattr(config, "get", fake_get)

    return apply


def ass_to_ms(value: str) -> int:
    hours, minutes, rest = value.split(":")
    seconds, centis = rest.split(".")

    return ((int(hours) * 60 + int(minutes)) * 60 + int(seconds)) * 1000 + int(centis) * 10


def dialogue_durations(ass: str) -> list[int]:
    result = []

    for line in ass.splitlines():
        if line.startswith("Dialogue:"):
            _, start, end = line.split(",")[:3]
            result.append(ass_to_ms(end) - ass_to_ms(start))

    return result


@pytest.mark.parametrize("mode, expected_ms", [(1, 7000), (4, 3000), (5, 3000)])
def test_duration_follows_config(app, durations, mode, expected_ms):
    durations(scroll = 7, static = 3)

    ass = DanmakuASS([{"stime": 1000, "mode": mode, "text": "测试"}], title = "t").generate()

    assert dialogue_durations(ass) == [expected_ms]
