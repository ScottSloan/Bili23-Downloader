"""
把桌面版用到的图标抽成前端可用的一份数据

    .venv/Scripts/python.exe scripts/gen_webui_icons.py
    .venv/Scripts/python.exe scripts/gen_webui_icons.py --check   # 只校验是否为最新

产物：`webui/src/components/Fluent/icons/settingIcons.ts`

## 为什么要生成而不是手抄

设置页每张卡片左边、解析页工具栏上都有图标，桌面版用的是 qfluentwidgets 的 FluentIcon
与本项目自己的 ExtendedFluentIcon。手抄的话，路径数据动辄几 KB，抄错一个字符就是一个畸形图形，
而且**换了图标没人会想起来同步**。从两边的 Qt 资源里直接取，改了重新跑一遍即可。

## 取自 Qt 资源而不是磁盘文件

`src/res/icon/` 在发布流程里会被删掉（程序只读编译后的 `resources_rc.py`），
从资源里取两边都在。qfluentwidgets 的图标本来就只存在于资源里。

## 颜色

原始 svg 把颜色写死成 `#000000`（深色主题另有一套 `_white` / `dark/`）。
前端用 `currentColor` 跟随文字颜色，一份文件够两种主题用，所以这里统一替换掉。
"""

from pathlib import Path
import os
import re
import sys
import tempfile

ROOT = Path(__file__).resolve().parent.parent

sys.path.insert(0, str(ROOT / "src"))

os.environ.setdefault("BILI23_DATA_DIR", tempfile.mkdtemp(prefix = "bili23-icons-"))
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

OUTPUT = ROOT / "webui" / "src" / "components" / "Fluent" / "icons" / "fluentIcons.ts"

# 前端的名字 → 资源路径。左边这些名字会出现在 spec.ts 里
ICONS = {
    # qfluentwidgets 自带
    "palette":           ":/qfluentwidgets/images/icons/Palette_black.svg",
    "language":          ":/qfluentwidgets/images/icons/Language_black.svg",
    "folder":            ":/qfluentwidgets/images/icons/Folder_black.svg",
    "setting":           ":/qfluentwidgets/images/icons/Setting_black.svg",
    "document":          ":/qfluentwidgets/images/icons/Document_black.svg",
    "download":          ":/qfluentwidgets/images/icons/Download_black.svg",
    "photo":             ":/qfluentwidgets/images/icons/Photo_black.svg",
    "bookShelf":         ":/qfluentwidgets/images/icons/BookShelf_black.svg",
    "cloudDownload":     ":/qfluentwidgets/images/icons/CloudDownload_black.svg",
    "video":             ":/qfluentwidgets/images/icons/Video_black.svg",
    "music":             ":/qfluentwidgets/images/icons/Music_black.svg",
    "code":              ":/qfluentwidgets/images/icons/Code_black.svg",
    "search":            ":/qfluentwidgets/images/icons/Search_black.svg",
    "history":           ":/qfluentwidgets/images/icons/History_black.svg",

    # 本项目补的（ExtendedFluentIcon）
    "comment":           ":/bili23/icon/light/comment.svg",
    "subtitles":         ":/bili23/icon/light/subtitles.svg",
    "fastDownload":      ":/bili23/icon/light/fast_download.svg",
    "server":            ":/bili23/icon/light/server.svg",
    "todo":              ":/bili23/icon/light/todo.svg",
    "options":           ":/bili23/icon/light/options.svg",
    "clear":             ":/bili23/icon/light/clear.svg",
}

def read_resource(path: str) -> str:
    from PySide6.QtCore import QFile, QIODevice

    file = QFile(path)

    if not file.open(QIODevice.OpenModeFlag.ReadOnly):
        raise FileNotFoundError(f"资源里没有 {path}")

    try:
        return bytes(file.readAll()).decode("utf-8")

    finally:
        file.close()

def extract(source: str) -> tuple:
    """从 svg 文本里取出 viewBox 与内层内容"""
    match = re.search(r"<svg\b([^>]*)>(.*)</svg>", source, re.S)

    if not match:
        raise ValueError("认不出的 svg 结构")

    attributes, body = match.group(1), match.group(2)

    view_box = re.search(r'viewBox\s*=\s*"([^"]+)"', attributes)

    if not view_box:
        raise ValueError("svg 上没有 viewBox")

    # 逗号分隔的 viewBox（本项目的图标是这种写法）浏览器也认，但统一成空格更保险
    box = view_box.group(1).replace(",", " ")
    box = re.sub(r"\s+", " ", box).strip()

    # 颜色交给 currentColor
    body = re.sub(r'(fill|stroke)\s*=\s*"#0{3,8}"', r'\1="currentColor"', body, flags = re.I)
    body = re.sub(r'(fill|stroke)\s*=\s*"black"', r'\1="currentColor"', body, flags = re.I)

    body = re.sub(r"<!--.*?-->", "", body, flags = re.S)
    # 标签之间的换行与缩进纯属体积
    body = re.sub(r">\s+<", "><", body)
    body = re.sub(r"\s+", " ", body).strip()

    return box, body

def build() -> str:
    lines = [
        "// 由 scripts/gen_webui_icons.py 从 Qt 资源生成，请勿手改",
        "//",
        "// 设置页卡片左边、解析页工具栏上的那些图标。名字与用它的地方写的 `icon` 一致。",
        "// 颜色已换成 currentColor，深浅主题共用一份。",
        "",
        "export interface FluentIconData {",
        "  viewBox: string",
        "  body: string",
        "}",
        "",
        "export const FLUENT_ICONS: Record<string, FluentIconData> = {",
    ]

    for name, path in ICONS.items():
        box, body = extract(read_resource(path))

        lines.append(f"  {name}: {{")
        lines.append(f"    viewBox: '{box}',")
        lines.append(f"    body: '{body.replace(chr(92), chr(92) * 2).replace(chr(39), chr(92) + chr(39))}',")
        lines.append("  },")

    lines.append("}")
    lines.append("")

    return "\n".join(lines)

def main() -> int:
    import res.resources_rc            # noqa: F401  本项目的图标
    import qfluentwidgets._rc.resource  # noqa: F401  qfluentwidgets 的图标

    content = build()

    if "--check" in sys.argv:
        current = OUTPUT.read_text(encoding = "utf-8") if OUTPUT.exists() else ""

        if current != content:
            print("图标数据已过期，请运行 scripts/gen_webui_icons.py")

            return 1

        print("图标数据是最新的")

        return 0

    OUTPUT.write_text(content, encoding = "utf-8")

    print(f"已写入 {OUTPUT.relative_to(ROOT)}（{len(ICONS)} 个图标，{len(content)} 字节）")

    return 0

if __name__ == "__main__":
    sys.exit(main())
