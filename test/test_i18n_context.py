"""
翻译上下文与代码的一致性。

Qt 的 self.tr() 按「上下文」查表，PySide6 在运行时用实例所属类的名字作为上下文，
未命中时沿 MRO 逐级回退到父类名。也就是说 .ts 里的 <context><name> 必须与
代码中某个真实存在的类同名，否则那一整组译文永远查不到。

这件事没有任何运行期报错 —— 界面只是默默显示英文原文。它尤其容易在重构时发生：

* 重命名一个类
* 把带 tr() 的方法挪进另一个类
* 合并或删除一个基类（该基类从 MRO 中消失，靠回退命中的译文随之失效）

本项目目前正好有这种结构：ParseInterface 自身没有登记译文，它的 4 条
"Skipped duplicate download" 之类的字符串登记在父类 ParseBase 名下，
靠 MRO 回退才生效；MainWindow 与 MainWindowBase 同理（12 条）。
若哪天把基类合并掉而没有同步 .ts，这些译文会无声失效。

因此这里把「每个类名形式的 context 都必须对应一个真实的类」钉成断言。
Translator 中用 QCoreApplication.translate() 显式指定的上下文
（EPISODE_TYPE、ERROR_MESSAGES 等，全大写下划线命名）不在此列。
"""

from pathlib import Path
import xml.etree.ElementTree as ET
import ast
import re

import pytest


ROOT = Path(__file__).resolve().parent.parent
TS_FILES = sorted((ROOT / "src" / "res" / "i18n").glob("*.ts"))

# Translator 中显式指定的上下文，全大写下划线命名，不对应任何类
EXPLICIT_CONTEXT = re.compile(r"^[A-Z][A-Z0-9_]*$")


def collect_class_names() -> set[str]:
    names = set()

    for path in (ROOT / "src").rglob("*.py"):
        if "resources_rc" in path.name or "dm_pb2" in path.name:
            continue

        try:
            tree = ast.parse(path.read_text(encoding = "utf-8"))
        except SyntaxError:
            continue

        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                names.add(node.name)

    return names


def collect_contexts(ts_path: Path) -> list[str]:
    root = ET.parse(ts_path).getroot()

    return [c.findtext("name") for c in root.findall("context")]


def test_ts_files_exist():
    assert TS_FILES, "未找到任何 .ts 翻译文件"


@pytest.mark.parametrize("ts_path", TS_FILES, ids = lambda p: p.name)
def test_every_class_context_matches_a_real_class(ts_path):
    classes = collect_class_names()

    missing = sorted(
        name for name in collect_contexts(ts_path)
        if name and not EXPLICIT_CONTEXT.match(name) and name not in classes
    )

    assert not missing, (
        f"{ts_path.name} 中以下 context 在代码里找不到同名类：{missing}。\n"
        "这些译文将永远无法命中，界面会显示英文原文。\n"
        "若是重命名或合并了类，请同步修改 .ts 中的 <name>，"
        "再用 pyside6-lrelease 重新生成 .qm 并用 pyside6-rcc 重新生成 resources_rc.py。"
    )


@pytest.mark.parametrize("ts_path", TS_FILES, ids = lambda p: p.name)
def test_explicit_contexts_are_declared_in_translator(ts_path):
    # 全大写的 context 由 Translator 显式指定，必须能在该模块里找到对应调用，
    # 否则同样是失效的译文
    translator_source = (ROOT / "src" / "util" / "common" / "translator.py").read_text(encoding = "utf-8")

    unused = sorted(
        name for name in collect_contexts(ts_path)
        if name and EXPLICIT_CONTEXT.match(name) and f'"{name}"' not in translator_source
    )

    # TERMS_OF_USE 等可能在别处使用，放宽到全项目搜索
    if unused:
        all_source = "\n".join(
            p.read_text(encoding = "utf-8")
            for p in (ROOT / "src").rglob("*.py")
            if "resources_rc" not in p.name and "dm_pb2" not in p.name
        )
        unused = [name for name in unused if f'"{name}"' not in all_source]

    assert not unused, f"{ts_path.name} 中以下显式 context 在代码里没有任何使用：{unused}"


class TestMroFallbackContexts:
    """
    记录当前依赖 MRO 回退才能生效的上下文。

    这些 context 对应的是基类，而实际被实例化的是它们的子类。译文能生效，
    靠的是 PySide6 在子类名未命中时回退到父类名。一旦基类被合并或删除，
    这层回退就没了。

    本用例不是要求保持现状，而是让这种隐式依赖显式可见：如果哪次重构确实
    移除了这些基类，用例会失败并提示需要同步 .ts。
    """

    KNOWN_BASE_CONTEXTS = ["ParseBase", "MainWindowBase"]

    @pytest.mark.parametrize("context", KNOWN_BASE_CONTEXTS)
    def test_base_class_still_in_mro(self, context):
        import importlib

        module_by_context = {
            "ParseBase": ("gui.interface.parse", "ParseInterface"),
            "MainWindowBase": ("gui.interface.main_window", "MainWindow"),
        }

        module_path, subclass_name = module_by_context[context]
        subclass = getattr(importlib.import_module(module_path), subclass_name)

        mro_names = [cls.__name__ for cls in subclass.__mro__]

        assert context in mro_names, (
            f"{context} 已不在 {subclass_name} 的 MRO 中，"
            f"登记在该 context 下的译文将失效。请把 .ts 里的 <name>{context}</name> "
            f"改为 {subclass_name}（与既有 context 合并），"
            "再重新生成 .qm 与 resources_rc.py。"
        )
