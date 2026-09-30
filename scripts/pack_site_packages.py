#!/usr/bin/env python3
"""
精简发布目录的 site-packages，并把纯 Python 依赖打成 deps.zip

便携版 zip 里散落着几百个 .py，与"便携 Python + pythonw + 一堆脚本"的
恶意软件分发形态高度相似，容易被杀软的云端 ML 盯上。这里做两件事：

    1. 删掉运行期根本用不到的目录（pywin32 的示例、测试、安装脚本等）
    2. 把 PURE_PACKAGES 里的包打进 site-packages\\deps.zip，由 zipimport 加载

zip 里每个模块同样存 .py 和 .pyc 两份（同 build_app_zip.py）：.pyc 用于执行，
.py 供 zipimporter.get_source() 使用，第三方库抛出的异常在崩溃日志里依旧
带着源码行。

必须在生成完整性清单之前运行 —— deps.zip 要被清单收录，被删掉的文件也
不能留在清单里。
"""

import argparse
import importlib.util
import marshal
import shutil
import struct
import sys
import zipfile
from pathlib import Path

# 同 build_app_zip.py：不显式指定的话，输出编码跟随系统 ANSI 代码页，
# 英文 Windows（cp1252）上中文 print 会抛 UnicodeEncodeError
sys.stdout.reconfigure(encoding = "utf-8", errors = "replace")
sys.stderr.reconfigure(encoding = "utf-8", errors = "replace")

ZIP_NAME = "deps.zip"

# 打进 zip 的顶层包 / 模块，均为纯 Python，且不靠 __file__ 读取随包的数据文件。
#
# 不在其列的都有原因，新增依赖时照此判断：
#   PySide6、shiboken6、orjson、psutil  带 .pyd/.dll，zipimport 加载不了扩展模块
#   google                              protobuf 依赖同一命名空间下的 _upb\_message.pyd，
#                                       命名空间包拆在 zip 与目录两处太脆弱
#   win32、pythoncom、pywin32_system32  靠 pywin32_bootstrap 与 DLL 目录搭起来的一整套
#   certifi                             cacert.pem 要以真实文件路径交给 ssl，放进 zip
#                                       只会被 importlib.resources 解压到临时目录
PURE_PACKAGES = [
    "darkdetect",
    "h11",
    "httpcore",
    "httpx",
    "idna",
    "qfluentwidgets",
    "qframelesswindow",
    "qrcode",
    "typing_extensions.py",
    "verhub_sdk",
]

# 运行期用不到、直接删除的目录（相对 site-packages）
STRIP_DIRS = [
    "win32/Demos",
    "win32/test",
    "win32/scripts",
    "certifi/tests",
]

# 扩展模块出现在上面的包里说明依赖升级后不再是纯 Python，得停下来重新评估
NATIVE_SUFFIXES = {".pyd", ".dll", ".so"}

SKIP_DIRS = {"__pycache__"}


def make_pyc(source: bytes, co_filename: str) -> bytes:
    """编译成 unchecked-hash 型 pyc（PEP 552）

    与 build_app_zip.py 不同，这里走的是标准 zipimport：timestamp 型 pyc 会拿去
    和 zip 里 .py 条目的时间比对，对不上就退回编译源码。unchecked-hash 型不做
    任何校验，直接执行 —— zip 已被完整性清单覆盖，源码不可能比字节码新
    """
    code = compile(source, co_filename, "exec", dont_inherit=True)

    # flags=0b01：hash-based，且不校验源码
    header = importlib.util.MAGIC_NUMBER + struct.pack("<I", 0b01) + importlib.util.source_hash(source)

    return header + marshal.dumps(code)


def iter_package(site: Path, name: str):
    """遍历一个顶层包 / 模块，返回 (绝对路径, zip 内相对路径)"""
    top = site / name

    if top.is_file():
        yield top, name
        return

    for path in sorted(top.rglob("*")):
        if not path.is_file():
            continue

        rel = path.relative_to(site)

        if any(part in SKIP_DIRS for part in rel.parts):
            continue

        yield path, rel.as_posix()


def strip(site: Path) -> int:
    removed = 0

    for rel in STRIP_DIRS:
        path = site / rel

        if not path.is_dir():
            print(f"[跳过] 不存在：{rel}")
            continue

        removed += sum(1 for p in path.rglob("*") if p.is_file())
        shutil.rmtree(path)

    return removed


def pack(site: Path, out: Path) -> int:
    # 先整体检查再动手，免得打包到一半才发现某个包带了扩展模块
    for name in PURE_PACKAGES:
        if not (site / name).exists():
            raise SystemExit(f"找不到依赖：{name}（runtime 里的依赖变了？同步更新 PURE_PACKAGES）")

        for path, arc in iter_package(site, name):
            if path.suffix.lower() in NATIVE_SUFFIXES:
                raise SystemExit(f"{arc} 是扩展模块，{name} 不能放进 zip，请从 PURE_PACKAGES 中移除")

    count = 0

    with zipfile.ZipFile(out, "w", zipfile.ZIP_DEFLATED, compresslevel=9) as zf:
        for name in PURE_PACKAGES:
            for path, arc in iter_package(site, name):
                data = path.read_bytes()
                entries = [(arc, data)]

                if arc.endswith(".py"):
                    # traceback 里显示的位置，与 app.zip 的 "script/<相对路径>" 同一口径
                    try:
                        entries.append((arc + "c", make_pyc(data, "site-packages/" + arc)))

                    except SyntaxError as e:
                        # 只丢字节码，源码照样进包，运行期由 zipimport 现场编译
                        print(f"[警告] {arc}: 语法错误 {e}", file=sys.stderr)

                    count += 1

                # 固定时间戳，同样的依赖每次构建产出同样的 zip（同 build_app_zip.py）
                for entry, payload in entries:
                    info = zipfile.ZipInfo(entry, date_time=(1980, 1, 1, 0, 0, 0))
                    info.compress_type = zipfile.ZIP_DEFLATED
                    info.external_attr = 0o644 << 16
                    zf.writestr(info, payload)

    for name in PURE_PACKAGES:
        path = site / name

        if path.is_dir():
            shutil.rmtree(path)
        else:
            path.unlink()

    return count


def main():
    parser = argparse.ArgumentParser(description="精简 site-packages 并把纯 Python 依赖打成 deps.zip")
    parser.add_argument("site", type=Path, help="发布目录里的 site-packages")

    args = parser.parse_args()

    if not args.site.is_dir():
        print(f"目录不存在：{args.site}", file=sys.stderr)
        return 1

    out = args.site / ZIP_NAME

    if out.exists():
        print(f"{out} 已存在，这个目录已经处理过了", file=sys.stderr)
        return 1

    # pyc 的 magic 与解释器版本绑定，构建用的 Python 必须与 runtime 同版本，
    # 否则 zipimport 会丢弃字节码、每次启动都重新编译源码
    print(f"构建用 Python: {sys.version.split()[0]} (magic {importlib.util.MAGIC_NUMBER.hex()})")

    removed = strip(args.site)
    print(f"已删除 {removed} 个运行期用不到的文件")

    count = pack(args.site, out)
    print(f"已打包 {count} 个模块 -> {out} ({out.stat().st_size / 1024:.1f} KB)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
