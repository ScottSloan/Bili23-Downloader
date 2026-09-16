"""
下载选项的固化与回落。

`601639a0` 把下载选项改成「创建任务时固化」，配套的回落是「任务里没这一项就取全局设置」。
`3cfb1a4d` 随后把进程级运行时状态从 APPConfig 剥离到了 runtime，于是
`keep_original_files_type` 在 config 上不再存在 —— 回落路径直接抛 AttributeError，
而 `snapshot()` 在 `TaskManager.create()` 里被无条件调用，表现为**任何下载任务都创建不了**
（弹「下载失败」的 toast，不崩溃）。当时整个测试套件都是绿的，因为没人断言过这条接缝。

因此这里钉住的核心是：`_OPTION_SPEC` 里的每一项都必须能取到全局值。
"""

import pytest


@pytest.fixture
def restore_runtime_option():
    # 这一项是进程级运行时状态，用例改完必须还原，否则会漏给后面的用例
    from util.common.runtime import runtime

    original = runtime.download.keep_original_files_type

    yield runtime.download

    runtime.download.keep_original_files_type = original


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


class TestRuntimeBackedOption:
    def test_snapshot_freezes_runtime_value(self, restore_runtime_option):
        from util.download.task.options import snapshot

        restore_runtime_option.keep_original_files_type = 2

        assert snapshot()["keep_original_files_type"] == 2

    def test_missing_option_falls_back_to_runtime(self, restore_runtime_option):
        # 旧版本创建的任务没有 Options 这一组，各项都是 None，此时读用户当前的全局设置
        from util.download.task.info import TaskInfo
        from util.download.task.options import resolve

        restore_runtime_option.keep_original_files_type = 2

        assert resolve(TaskInfo(), "keep_original_files_type") == 2

    def test_frozen_option_wins_over_runtime(self, restore_runtime_option):
        from util.common.enum import OriginalFileType
        from util.download.task.info import TaskInfo
        from util.download.task.options import resolve

        restore_runtime_option.keep_original_files_type = 2

        task_info = TaskInfo()
        task_info.Options.keep_original_files_type = OriginalFileType.VIDEO.value

        assert resolve(task_info, "keep_original_files_type") == OriginalFileType.VIDEO.value
