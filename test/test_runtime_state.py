"""
util/common/runtime.py —— 进程级运行时状态，以及它与 config 的边界。

阶段 2 把 21 个运行时属性从 APPConfig 上剥离。分家的意义在于消除一个
具体的出错来源：两类状态过去挂在同一个对象上，写法却长得几乎一样，
一个写磁盘、一个只在内存里，读代码时分不出来。

本文件守两条不变量：
  1. runtime 不持久化，也不依赖配置系统；
  2. APPConfig 上不再出现可变的运行时状态。

第 2 条是会随时间退化的那种 —— 下次有人需要一个"全局临时变量"时，
APPConfig 依然是最顺手的地方。因此用测试挡住，而不是靠注释约定。
"""

from util.common.config import APPConfig
from util.common.runtime import RuntimeState, runtime

from qfluentwidgets import ConfigItem

import subprocess
import sys


class TestStructure:
    def test_groups_present(self):
        assert set(vars(runtime)) == {"auth", "ffmpeg", "download", "mcp", "naming", "app"}

    def test_is_a_singleton_instance(self):
        assert isinstance(runtime, RuntimeState)

    def test_fresh_instance_has_defaults(self):
        # 每个分组都必须能独立构造出一份默认值，便于测试里替换
        fresh = RuntimeState()

        assert fresh.app.main_window_ready is False
        assert fresh.auth.is_expired is False
        assert fresh.ffmpeg.unavailable is True
        assert fresh.download.video_quality_id == 200
        assert fresh.naming.global_starting_number == 1
        assert fresh.mcp.running is False


class TestNoPersistence:
    def test_runtime_does_not_import_config(self):
        # runtime 必须保持零依赖：它被 signal_bus 等底层模块导入，
        # 一旦反向依赖 config，就会把整套 Qt 配置机制拖进这些调用路径
        source = (
            __import__("pathlib").Path(__file__).parent.parent
            / "src" / "util" / "common" / "runtime.py"
        ).read_text(encoding = "utf-8")

        code_lines = [
            line for line in source.splitlines()
            if line.startswith(("import ", "from "))
        ]

        assert code_lines == [], f"runtime.py 不应有任何导入，实际存在：{code_lines}"

    def test_importing_runtime_does_not_load_qt(self):
        # 在干净的子进程里验证 —— 本进程早已因其他用例加载了 Qt
        result = subprocess.run(
            [sys.executable, "-c",
             "import sys; sys.path.insert(0, 'src');"
             "import util.common.runtime;"
             "print(any(m.startswith('PySide6') for m in sys.modules))"],
            cwd = __import__("pathlib").Path(__file__).parent.parent,
            capture_output = True, text = True, timeout = 60,
        )

        assert result.returncode == 0, result.stderr
        assert result.stdout.strip().splitlines()[-1] == "False", (
            "导入 runtime 时拖入了 Qt，它不再是零依赖模块"
        )


class TestConfigBoundary:
    # 版本号等静态常量，不是运行时状态，允许留在 APPConfig 上
    ALLOWED_PLAIN_ATTRS = {
        "app_name", "app_version", "app_comparable_version", "app_config_version",
        "staticMetaObject",     # Qt 元对象
    }

    def test_no_mutable_runtime_state_on_config(self):
        """
        APPConfig 上除 ConfigItem 外，只应剩下静态常量。

        新增一个裸类属性会让本用例失败 —— 这是有意为之：
        需要进程级可变状态时，应加到 runtime.py 的对应分组里，
        而不是挂回 APPConfig，否则 `config.x = v`（不落盘）与
        `config.set(config.x, v)`（落盘）的混淆会重新出现。
        """
        plain = {
            name for name, value in vars(APPConfig).items()
            if not name.startswith("_")
            and not isinstance(value, ConfigItem)
            and not callable(value)
            and not isinstance(value, (classmethod, staticmethod, property))
        }

        unexpected = plain - self.ALLOWED_PLAIN_ATTRS

        assert not unexpected, (
            f"APPConfig 上出现了新的非 ConfigItem 属性：{sorted(unexpected)}。"
            "若这是进程级运行时状态，请加到 util/common/runtime.py；"
            "若是静态常量，请加入本用例的 ALLOWED_PLAIN_ATTRS。"
        )

    def test_migrated_attributes_are_gone(self):
        # 逐个确认已迁走的属性不会因为合并冲突等原因被还原回来
        migrated = [
            "is_expired", "user_uname", "user_uid", "user_avatar_pixmap",
            "ffmpeg_executable", "bundle_ffmpeg_exist", "no_ffmpeg_available",
            "video_quality_id", "audio_quality_id", "video_codec_id",
            "download_video_stream", "download_audio_stream", "merge_video_audio",
            "keep_original_files", "keep_original_files_type",
            "mcp_running", "mcp_last_error",
            "target_naming_rule_id", "global_starting_number", "current_starting_number",
            "main_window_ready",
        ]

        still_there = [name for name in migrated if name in vars(APPConfig)]

        assert not still_there, f"这些属性已迁往 runtime，不应再出现在 APPConfig：{still_there}"


class TestSignalBusDecoupled:
    def test_signal_bus_uses_runtime_not_config(self):
        # signal_bus 过去仅为 main_window_ready 一个字段就依赖整个配置系统
        import util.common.signal_bus as bus

        assert hasattr(bus, "runtime")
        assert not hasattr(bus, "config"), "signal_bus 不应再依赖 config"

    def test_pending_signals_gate_reads_runtime(self):
        from util.common.signal_bus import SignalBus

        bus = SignalBus()
        original = runtime.app.main_window_ready

        try:
            runtime.app.main_window_ready = False
            bus.emit_signal(bus.toast.show, None, "t", "m")

            assert len(bus.pending_signals) == 1, "主窗口未就绪时信号应排队"
        finally:
            runtime.app.main_window_ready = original
