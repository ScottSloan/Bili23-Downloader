#!/usr/bin/env python3
"""
生成完整性清单，供 loader 在加载 Python 之前逐个核对

清单本身嵌进 exe 的资源段，与内嵌源码一样受 Authenticode 覆盖 —— 于是不需要
任何私钥或非对称签名：改清单等于改 exe，签名当场失效。

清单覆盖 runtime、site-packages、bundle 等一切随包发布的文件。exe 自己不在其中：
它由代码签名保护，也没法自己算自己的哈希（签名数据就在文件里）。

格式（小端）：
    magic   4 字节  "PSM1"
    count   uint32  条目数
    条目 × count：
        uint16  路径的 UTF-8 字节长度
        bytes   相对根目录的路径，一律用反斜杠分隔
        32 字节 SHA-256
"""

import argparse
import hashlib
import struct
import sys
from pathlib import Path

# 同 build_app_zip.py：不显式指定的话，输出编码跟随系统 ANSI 代码页，
# 英文 Windows（cp1252）上中文 print 会抛 UnicodeEncodeError
sys.stdout.reconfigure(encoding = "utf-8", errors = "replace")
sys.stderr.reconfigure(encoding = "utf-8", errors = "replace")

MAGIC = b"PSM1"

# 与 loader 侧的 kCodeExtensions 对照用。清单本身收录发布目录里的**每个**文件，
# 不按类型筛选，所以这份列表不参与生成；它记录的是 loader 的判定口径：
# 这些类型出现在受管目录里却不在清单中，会被拒绝启动（挡 .pth 注入、DLL 投放，
# 以及往 webui 里塞脚本）。改了 loader 那边，记得同步这里。
CODE_EXTENSIONS = {
    "py", "pyc", "pyd", "pyw", "pyo", "pyz",
    "dll", "exe", "com", "ocx", "sys", "drv", "scr",
    "so", "pth", "_pth", "zip", "cat",
    "js", "mjs", "html", "htm", "css",
}

# 不进清单的目录：构建残留与运行期产物
SKIP_DIRS = {"__pycache__", ".git"}


def iter_files(root: Path, exclude: set):
    for path in sorted(root.rglob("*")):
        if not path.is_file():
            continue

        rel = path.relative_to(root)

        if any(part in SKIP_DIRS for part in rel.parts):
            continue
        if str(rel).lower() in exclude:
            continue

        yield path, rel


def sha256(path: Path) -> bytes:
    h = hashlib.sha256()

    with path.open("rb") as f:
        while chunk := f.read(1 << 20):
            h.update(chunk)

    return h.digest()


def build(root: Path, out: Path, exclude: set) -> tuple:
    entries = []
    total = 0

    for path, rel in iter_files(root, exclude):
        # 统一成反斜杠，loader 侧遍历目录拿到的也是这个形态
        name = str(rel).replace("/", "\\").encode("utf-8")

        if len(name) > 0xFFFF:
            print(f"[跳过] 路径过长：{rel}", file=sys.stderr)
            continue

        entries.append((name, sha256(path)))
        total += path.stat().st_size

    blob = bytearray(MAGIC + struct.pack("<I", len(entries)))

    for name, digest in entries:
        blob += struct.pack("<H", len(name)) + name + digest

    out.parent.mkdir(parents=True, exist_ok=True)
    out.write_bytes(bytes(blob))

    return len(entries), total, len(blob)


def main():
    parser = argparse.ArgumentParser(description="生成 PyStand 完整性清单")
    parser.add_argument("root", type=Path, help="发布目录根（PYSTAND_HOME）")
    parser.add_argument("-o", "--output", type=Path, default=Path("manifest.bin"))
    parser.add_argument("--exclude", action="append", default=[],
                        help="不纳入清单的文件，相对根目录（可重复）。启动器自身必须排除")

    args = parser.parse_args()

    if not args.root.is_dir():
        print(f"目录不存在：{args.root}", file=sys.stderr)
        return 1

    exclude = {e.replace("/", "\\").lower() for e in args.exclude}

    count, total, size = build(args.root, args.output, exclude)

    print(f"已收录 {count} 个文件，共 {total / 1048576:.1f} MB")
    print(f"清单 -> {args.output} ({size / 1024:.1f} KB)")

    if exclude:
        print(f"已排除：{', '.join(sorted(exclude))}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
