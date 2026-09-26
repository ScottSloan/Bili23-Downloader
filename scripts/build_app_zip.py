#!/usr/bin/env python3
"""
把应用源码打成可嵌进 PyStand.exe 的 app.zip

zip 里每个模块存两份：.pyc 用于执行（省去每次启动重新编译的开销），
.py 用于 traceback —— 内存加载的模块在磁盘上没有对应文件，linecache
只能通过 loader.get_source() 拿到源码行，少了 .py 崩溃日志里就只剩行号。

co_filename 在编译期固定，运行期改不了（嵌套的函数各自持有一份），
所以这里就把它定成 "script/<相对路径>" —— traceback 里看到的仍是熟悉的
模块位置，只是分隔符换成了正斜杠。
"""

import argparse
import importlib.util
import marshal
import struct
import sys
import zipfile
from pathlib import Path

# 输出的编码默认跟着系统 ANSI 代码页走：英文 Windows 是 cp1252，编不了中文，
# 下面那些 print 会直接抛 UnicodeEncodeError 而不是显示成乱码 —— CI 上正是栽在
# 这里，本地简中是 cp936 反而一路正常。显式指定，脚本不看环境脸色
sys.stdout.reconfigure(encoding = "utf-8", errors = "replace")
sys.stderr.reconfigure(encoding = "utf-8", errors = "replace")

# 不进包的目录：缓存、版本控制、开发期产物
EXCLUDE_DIRS = {"__pycache__", ".git", ".idea", ".vscode", "node_modules"}


def make_pyc(source: bytes, co_filename: str) -> bytes:
    """编译成 pyc 字节流（3.7+ 的 16 字节头 + marshal 数据）"""
    code = compile(source, co_filename, "exec", dont_inherit=True)

    # flags=0 表示 timestamp 型；mtime 与 size 置零，因为失效判断由我们自己
    # 接管（zip 与 exe 一同被 Authenticode 覆盖，不存在源码比字节码新的情况）
    header = importlib.util.MAGIC_NUMBER + struct.pack("<III", 0, 0, len(source))

    return header + marshal.dumps(code)


def collect(src: Path):
    """遍历出所有要打包的 .py，返回 (绝对路径, zip 内相对路径)"""
    for path in sorted(src.rglob("*.py")):
        if any(part in EXCLUDE_DIRS for part in path.relative_to(src).parts):
            continue

        yield path, path.relative_to(src).as_posix()


def build(src: Path, out: Path, compress: bool) -> int:
    mode = zipfile.ZIP_DEFLATED if compress else zipfile.ZIP_STORED
    count = 0

    out.parent.mkdir(parents=True, exist_ok=True)

    with zipfile.ZipFile(out, "w", mode, compresslevel=9 if compress else None) as zf:
        for abs_path, arc in collect(src):
            source = abs_path.read_bytes()

            # traceback 里显示的位置。用正斜杠与 zip 内路径保持一致 ——
            # 分隔符形态不影响任何功能，却能躲开 C++ raw string 里写反斜杠
            # 的一连串转义陷阱（引导脚本那侧同样是 "script/"）
            co_filename = "script/" + arc

            try:
                pyc = make_pyc(source, co_filename)

            except SyntaxError as e:
                print(f"[跳过] {arc}: 语法错误 {e}", file=sys.stderr)
                continue

            # 用固定时间戳写入。writestr 传字符串名时会取当前时间，同样的源码
            # 每次构建都会产出不同的 zip，exe 的哈希也就跟着变 —— 那样既无法
            # 复现构建，上传前拿哈希判断"要不要重传"也失去意义
            for name, payload in ((arc, source), (arc[:-3] + ".pyc", pyc)):
                info = zipfile.ZipInfo(name, date_time=(1980, 1, 1, 0, 0, 0))
                info.compress_type = mode
                info.external_attr = 0o644 << 16
                zf.writestr(info, payload)

            count += 1

    return count


def main():
    parser = argparse.ArgumentParser(description="打包应用源码为 app.zip")
    parser.add_argument("src", type=Path, help="源码根目录（如 Bili23 的 src/）")
    parser.add_argument("-o", "--output", type=Path, default=Path("app.zip"))
    parser.add_argument("--no-compress", action="store_true", help="不压缩，便于排查")

    args = parser.parse_args()

    if not args.src.is_dir():
        print(f"源码目录不存在：{args.src}", file=sys.stderr)
        return 1

    # pyc 的 magic 与解释器版本绑定，构建用的 Python 必须与 runtime 同版本，
    # 否则运行期只能回退到编译 .py —— 能跑，但白白付出启动开销
    print(f"构建用 Python: {sys.version.split()[0]} (magic {importlib.util.MAGIC_NUMBER.hex()})")

    count = build(args.src, args.output, not args.no_compress)
    size = args.output.stat().st_size

    print(f"已打包 {count} 个模块 -> {args.output} ({size / 1024:.1f} KB)")

    return 0


if __name__ == "__main__":
    sys.exit(main())
