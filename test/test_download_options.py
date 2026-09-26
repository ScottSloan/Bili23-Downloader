"""
下载选项的固化与回落。

`601639a0` 把下载选项改成「创建任务时固化」，配套的回落是「任务里没这一项就取全局设置」。
`3cfb1a4d` 随后把进程级运行时状态从 APPConfig 剥离到了 runtime，于是
`keep_original_files_type` 在 config 上不再存在 —— 回落路径直接抛 AttributeError，
而 `snapshot()` 在 `TaskManager.create()` 里被无条件调用，表现为**任何下载任务都创建不了**
（弹「下载失败」的 toast，不崩溃）。当时整个测试套件都是绿的，因为没人断言过这条接缝。

因此这里钉住的核心是：`_OPTION_SPEC` 里的每一项都必须能取到全局值。

回落源后来统一收敛回了 config：媒体选项既能按次指定、也是用户的长期偏好，设置界面
与下载选项对话框改的是同一份值（详见 config.py 里 download_video_stream 那一段）。
`_RUNTIME_FALLBACK` 那张表随之取消，「回落源是 config 上的同名 ConfigItem」不再有例外，
上面那条用例因此比以前更有约束力。
"""

import pytest


@pytest.fixture
def restore_option():
    # config.set() 会落盘并在本场测试内一直生效，用例改完必须还原
    from util.common.config import config

    original = config.get(config.keep_original_files_type)

    yield config

    config.set(config.keep_original_files_type, original)


class TestGlobalFallback:
    def test_every_option_has_a_resolvable_global_value(self):
        # 往 _OPTION_SPEC 加选项却忘了同时给出回落源时，这条会立刻失败 ——
        # 而不是一路藏到用户点下载才炸
        from util.download.task.options import _OPTION_SPEC, _global_value

        for key in _OPTION_SPEC:
            _global_value(key)

    def test_snapshot_covers_every_option(self):
        from util.download.task.options import _OPTION_SPEC, snapshot

        assert set(snapshot()) == set(_OPTION_SPEC)


class TestKeepOriginalFilesType:
    """
    `keep_original_files_type` 是 _OPTION_SPEC 里唯一需要转成枚举再存的一项，
    也是回落源从 runtime 改回 config 的那一项，单独钉住它的取值链
    """

    def test_snapshot_freezes_config_value(self, restore_option):
        from util.common.enum import OriginalFileType
        from util.download.task.options import snapshot

        restore_option.set(restore_option.keep_original_files_type, OriginalFileType.AUDIO)

        assert snapshot()["keep_original_files_type"] == OriginalFileType.AUDIO.value

    def test_missing_option_falls_back_to_config(self, restore_option):
        # 旧版本创建的任务没有 Options 这一组，各项都是 None，此时读用户当前的全局设置
        from util.common.enum import OriginalFileType
        from util.download.task.info import TaskInfo
        from util.download.task.options import resolve

        restore_option.set(restore_option.keep_original_files_type, OriginalFileType.AUDIO)

        assert resolve(TaskInfo(), "keep_original_files_type") == OriginalFileType.AUDIO

    def test_frozen_option_wins_over_config(self, restore_option):
        from util.common.enum import OriginalFileType
        from util.download.task.info import TaskInfo
        from util.download.task.options import resolve

        restore_option.set(restore_option.keep_original_files_type, OriginalFileType.AUDIO)

        task_info = TaskInfo()
        task_info.Options.keep_original_files_type = OriginalFileType.VIDEO.value

        assert resolve(task_info, "keep_original_files_type") == OriginalFileType.VIDEO
