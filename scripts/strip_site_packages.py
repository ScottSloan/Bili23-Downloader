#!/usr/bin/env python3
"""
精简发布目录的 site-packages，删掉运行期根本用不到的目录

便携版 zip 里散落着几百个 .py，与"便携 Python + pythonw + 一堆脚本"的
恶意软件分发形态高度相似，容易被杀软的云端 ML 盯上。其中 pywin32 的示例、
测试与安装脚本占了大头，而它们在运行期一个都用不到。

必须在生成完整性清单之前运行 —— 被删掉的文件不能留在清单里。
"""

import argparse
import shutil
import sys
from pathlib import Path

# 同 build_app_zip.py：不显式指定的话，输出编码跟随系统 ANSI 代码页，
# 英文 Windows（cp1252）上中文 print 会抛 UnicodeEncodeError
sys.stdout.reconfigure(encoding = "utf-8", errors = "replace")
sys.stderr.reconfigure(encoding = "utf-8", errors = "replace")

# 运行期用不到、直接删除的目录（相对 site-packages）
STRIP_DIRS = [
    "win32/Demos",
    "win32/test",
    "win32/scripts",
    "certifi/tests",
]


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


def main():
    parser = argparse.ArgumentParser(description="精简 site-packages，删掉运行期用不到的目录")
    parser.add_argument("site", type=Path, help="发布目录里的 site-packages")

    args = parser.parse_args()

    if not args.site.is_dir():
        print(f"目录不存在：{args.site}", file=sys.stderr)
        return 1

    removed = strip(args.site)
    print(f"已删除 {removed} 个运行期用不到的文件")

    return 0


if __name__ == "__main__":
    sys.exit(main())
