"""
媒体选项卡片：装载、写回，以及它在两个入口下的不同时机。

这几项（下载哪几路流、下完之后怎么处理）原先挂在 runtime 上，只有下载选项对话框
能改 —— 打开对话框、勾一下、点确定，改动才落进「下一个任务用什么参数」的暂存里，
重启即失。改回 config 之后多了一个入口（设置界面），两个入口的差别只在**何时写回**：

    设置界面        改一下立即 save()，没有「确定」按钮
    下载选项对话框   accept() 时才 save()，关掉等于取消

因此卡片自己不决定时机，只发 changed 并由调用方连接 save()。这里钉住的就是这条缝：
装载时若误发 changed，设置界面一打开就会把界面上那几项写回配置，把用户的值冲掉。
"""

from PySide6.QtWidgets import QApplication, QWidget

import pytest


OPTIONS = [
    "download_video_stream",
    "download_audio_stream",
    "merge_video_audio",
    "keep_original_files",
    "keep_original_files_type",
]


@pytest.fixture(scope = "module")
def app():
    instance = QApplication.instance() or QApplication([])

    import res.resources_rc   # noqa: F401  图标与样式表由此注册，构造控件时会用到

    return instance


@pytest.fixture
def restore_config():
    # config.set() 会落盘并在本场测试内一直生效，用例改完必须还原
    from util.common.config import config

    original = {name: config.get(getattr(config, name)) for name in OPTIONS}

    yield config

    for name, value in original.items():
        config.set(getattr(config, name), value)


@pytest.fixture
def make_card(app, restore_config):
    from gui.component.setting import MediaOptionsCard

    parent = QWidget()
    cards = []

    def factory():
        card = MediaOptionsCard(None, parent = parent)
        cards.append(card)

        return card

    yield factory

    for card in cards:
        card.deleteLater()

    parent.deleteLater()


class TestLoad:
    def test_loads_from_config(self, make_card, restore_config):
        restore_config.set(restore_config.download_video_stream, False)
        restore_config.set(restore_config.download_audio_stream, True)
        restore_config.set(restore_config.merge_video_audio, True)
        restore_config.set(restore_config.keep_original_files, True)

        card = make_card()

        assert card.download_video_stream is False
        assert card.download_audio_stream is True
        assert card.keep_original_files is True

    def test_load_does_not_write_back(self, make_card, restore_config):
        # 装载期间发 changed，设置界面一打开就会把这几项写回配置 ——
        # 界面上的联动（关掉合并就取消保留原始文件）会顺势覆盖用户的值
        from util.common.enum import OriginalFileType

        restore_config.set(restore_config.download_video_stream, False)
        restore_config.set(restore_config.download_audio_stream, False)
        restore_config.set(restore_config.merge_video_audio, False)
        restore_config.set(restore_config.keep_original_files, False)
        restore_config.set(restore_config.keep_original_files_type, OriginalFileType.AUDIO)

        card = make_card()

        changes = []
        card.changed.connect(lambda: changes.append(True))
        card.on_load()

        assert changes == []
        assert restore_config.get(restore_config.keep_original_files_type) == OriginalFileType.AUDIO


class TestSave:
    def test_save_writes_every_option(self, make_card, restore_config):
        from util.common.enum import OriginalFileType

        card = make_card()

        card.download_video_stream_switch.setChecked(True)
        card.download_audio_stream_switch.setChecked(True)
        card.original_files_type_choice.setCurrentIndex(OriginalFileType.VIDEO.value)
        card.keep_original_files_switch.setChecked(True)

        card.save()

        assert restore_config.get(restore_config.download_video_stream) is True
        assert restore_config.get(restore_config.download_audio_stream) is True
        assert restore_config.get(restore_config.keep_original_files) is True
        assert restore_config.get(restore_config.keep_original_files_type) == OriginalFileType.VIDEO

    def test_changed_fires_on_user_edit(self, make_card, restore_config):
        card = make_card()

        changes = []
        card.changed.connect(lambda: changes.append(True))

        card.download_video_stream_switch.setChecked(False)

        assert changes, "用户改动没有触发 changed，设置界面里就永远不会落盘"

    def test_round_trip(self, make_card, restore_config):
        from util.common.enum import OriginalFileType

        card = make_card()

        card.original_files_type_choice.setCurrentIndex(OriginalFileType.AUDIO.value)
        card.keep_original_files_switch.setChecked(True)
        card.save()

        assert make_card().original_files_type_choice.currentIndex() == OriginalFileType.AUDIO.value
        assert make_card().keep_original_files is True
