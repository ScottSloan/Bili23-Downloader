"""
所选视频编码取不到时的回退提示（Issue #465）。

B 站不会为每个稿件都转码全部编码：刚投稿的稿件往往只有 AVC，而用户可以在
下载选项里选 AV1。解析层遇到这种情况会静默回落到优先级里第一个可用编码
（`VideoInfoParser.get_video_info` 与 `supplement_video_info` 各有一处），
于是「用户选的编码」与「实际下载的编码」之间没有任何提示。

Issue #465 报告者遇到的就是这个：编码下拉框显示 AV1，只有右侧一行灰字写着
AVC/H.264，与画质、码率、文件大小并排放在一起。他盯着那行看了半天，仍然以为
下载的是自己选的 AV1，直到用 MediaInfo 打开成品才发现。

因此这里钉住两层：
  1. `warn_codec_fallback()` 只在真的回退时发提示，且同一组合只发一次；
  2. `MediaInfoCard` 在回退时把提示以警示行显示出来，不再混在灰色小字里。
"""

from PySide6.QtWidgets import QApplication, QWidget

import pytest


@pytest.fixture(scope = "module")
def app():
    instance = QApplication.instance() or QApplication([])

    import res.resources_rc   # noqa: F401  图标与样式表由此注册，构造控件时会用到

    return instance


@pytest.fixture
def warning_sink():
    """收集 warn_codec_fallback() 发出的提示，并保证提示记录在用例前后都是干净的"""
    from util.common.signal_bus import signal_bus
    from util.download.parse import video_info

    messages = []

    def handler(category, title, content):
        messages.append((category, title, content))

    signal_bus.toast.show.connect(handler)
    video_info._warned_codec_fallback.clear()

    try:
        yield messages

    finally:
        signal_bus.toast.show.disconnect(handler)
        video_info._warned_codec_fallback.clear()


class TestDownloadSideWarning:
    def test_fallback_emits_a_warning(self, warning_sink):
        from util.common.enum import ToastNotificationCategory
        from util.download.parse.video_info import warn_codec_fallback

        warn_codec_fallback(13, 7)

        assert len(warning_sink) == 1

        category, _, content = warning_sink[0]

        assert category == ToastNotificationCategory.WARNING
        assert "AV1" in content
        assert "AVC/H.264" in content

    def test_same_pair_warns_only_once(self, warning_sink):
        # 一批任务里整个合集都缺同一个编码是常态，逐条弹提示会叠满屏幕
        from util.download.parse.video_info import warn_codec_fallback

        warn_codec_fallback(13, 7)
        warn_codec_fallback(13, 7)

        assert len(warning_sink) == 1

    def test_different_pair_warns_again(self, warning_sink):
        # 8K 档没有 AV1 而回落成 HEVC，与整个稿件就没有 AV1 是两回事
        from util.download.parse.video_info import warn_codec_fallback

        warn_codec_fallback(13, 7)
        warn_codec_fallback(13, 12)

        assert len(warning_sink) == 2

    def test_no_warning_when_codec_matches(self, warning_sink):
        from util.download.parse.video_info import warn_codec_fallback

        warn_codec_fallback(13, 13)

        assert warning_sink == []

    def test_no_warning_for_auto(self, warning_sink):
        # 20 是「自动（按优先级）」，按优先级挑编码本来就是它的行为
        from util.download.parse.video_info import warn_codec_fallback

        warn_codec_fallback(20, 7)
        warn_codec_fallback(None, 7)

        assert warning_sink == []


class TestDialogWarning:
    @pytest.fixture
    def card(self, app):
        from gui.dialog.download_options.card import MediaInfoCard
        from util.common.data import video_codec_map

        # 父控件必须活到用例结束：它一旦被回收，卡片会跟着一起销毁，
        # 后续调用打在已释放的 C++ 对象上
        parent = QWidget()
        card = MediaInfoCard(None, parent = parent)

        # 编码下拉框得先有可选项，currentData() 才取得到用户选的编码
        card.update_choice_data({}, {}, video_codec_map)

        yield card

        card.deleteLater()
        parent.deleteLater()

    def test_warning_shown_when_selected_codec_is_unavailable(self, card):
        card.video_codec_widget.choice.set_current_data(13)

        card.update_video_codec_description({"codec_id": 7})

        warning = card.video_codec_group.warningLabel

        assert not warning.isHidden()
        assert "AV1" in warning.text()

        # 实际编码紧挨在提示前面，提示里不再重复一遍，免得把这一行撑长
        assert "AVC/H.264" not in warning.text()
        assert card.video_codec_group.contentLabel.text() == "AVC/H.264"

    def test_common_tip_is_dropped_on_fallback(self, card):
        # 回退时这一行让给「实际编码 + 为什么不是它」，体积/兼容性那句通用说明
        # 再往后接就会把右侧的编码下拉框挤出卡片
        card.video_codec_widget.choice.set_current_data(7)

        card.update_video_codec_description({"codec_id": 7})

        assert card.video_codec_group.contentLabel.text() != "AVC/H.264"

    def test_warning_cleared_when_codec_is_available(self, card):
        card.video_codec_widget.choice.set_current_data(13)
        card.update_video_codec_description({"codec_id": 7})

        card.update_video_codec_description({"codec_id": 13})

        assert card.video_codec_group.warningLabel.isHidden()

    def test_no_warning_for_auto(self, card):
        card.video_codec_widget.choice.set_current_data(20)

        card.update_video_codec_description({"codec_id": 7})

        assert card.video_codec_group.warningLabel.isHidden()

    def test_warning_cleared_before_requery(self, card):
        # 重新查询期间上一组的回退提示必须撤下，否则会挂在那里与新结果对不上
        card.video_codec_widget.choice.set_current_data(13)
        card.update_video_codec_description({"codec_id": 7})

        card.pre_query_video_info()

        assert card.video_codec_group.warningLabel.isHidden()
