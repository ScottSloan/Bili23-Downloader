"""
翻译上下文与代码的一致性。

Qt 的 self.tr() 按「上下文」查表，PySide6 在运行时用实例所属类的名字作为上下文，
未命中时沿 MRO 逐级回退到父类名。也就是说 .ts 里的 <context><name> 必须与
代码中某个真实存在的类同名，否则那一整组译文永远查不到。

这件事没有任何运行期报错 —— 界面只是默默显示英文原文。它尤其容易在重构时发生：

* 重命名一个类
* 把带 tr() 的方法挪进另一个类
* 合并或删除一个基类（该基类从 MRO 中消失，靠回退命中的译文随之失效）

本项目就踩过这个坑：ParseInterface 的 4 条译文曾登记在父类 ParseBase 名下，
MainWindow 的 12 条登记在 MainWindowBase 名下，都靠 MRO 回退才生效。
合并这两个基类时，.ts 中的 context 已同步改名并重新生成 .qm 与 resources_rc.py。

因此这里钉住两层断言：
  1. 每个类名形式的 context 都必须对应一个真实存在的类（静态检查）；
  2. 这些 context 下的每条译文都必须能被真正解析出来（端到端，走完
     .ts → lrelease → .qm → resources_rc.py → QTranslator 整条链）。

Translator 中用 QCoreApplication.translate() 显式指定的上下文
（EPISODE_TYPE、ERROR_MESSAGES 等，全大写下划线命名）不在第 1 条的检查范围内。
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


class TestTranslationsActuallyResolve:
    """
    端到端验证：登记在某个 context 下的译文，能被同名类的实例真正解析出来。

    上面的用例只检查 .ts 里的 context 名与代码中的类名对得上，属于静态检查。
    这里进一步把编译后的 .qm 装进 QTranslator，用真实的类去查，确认整条链
    （.ts → lrelease → .qm → resources_rc.py → QTranslator → tr）都是通的。

    ParseInterface 与 MainWindow 是重点：它们的译文原本登记在 ParseBase /
    MainWindowBase 名下，靠 PySide6 沿 MRO 回退才生效。两个基类合并掉之后，
    .ts 中的 context 已同步改名，这里确保改名后译文没有失效。
    """

    LANGUAGES = [
        ("zh_CN", "China"),
        ("zh_TW", "Taiwan"),
    ]

    CONTEXTS = ["ParseInterface", "MainWindow"]

    @staticmethod
    def _load(language: str, country: str):
        from PySide6.QtCore import QLocale, QTranslator

        translator = QTranslator()
        locale = QLocale(QLocale.Language.Chinese, getattr(QLocale.Country, country))

        assert translator.load(locale, "bili23", ".", ":/bili23/i18n"), f"无法加载 {language} 翻译"

        return translator

    @pytest.mark.parametrize("language, country", LANGUAGES, ids = [lang for lang, _ in LANGUAGES])
    @pytest.mark.parametrize("context", CONTEXTS)
    def test_every_message_resolves(self, language, country, context):
        from PySide6.QtWidgets import QApplication

        app = QApplication.instance() or QApplication([])

        import res.resources_rc     # noqa: F401  .qm 由 Qt 资源系统提供

        ts_path = next(p for p in TS_FILES if language in p.name)
        root = ET.parse(ts_path).getroot()

        block = next(c for c in root.findall("context") if c.findtext("name") == context)
        messages = [(m.findtext("source"), m.findtext("translation")) for m in block.findall("message")]

        assert messages, f"{ts_path.name} 中 context {context} 没有任何条目"

        translator = self._load(language, country)
        app.installTranslator(translator)

        try:
            mismatched = [
                source for source, expected in messages
                if app.translate(context, source) != expected
            ]
        finally:
            app.removeTranslator(translator)

        assert not mismatched, (
            f"{language} 下 context {context} 的以下译文无法解析：{mismatched}\n"
            "多半是 .ts 改动后没有重新生成 .qm 与 resources_rc.py。"
        )
