"""
ASS 颜色字符串的解析与生成

ASS 的颜色是 `&HAABBGGRR`：**字节序与常见的 RGB 相反**，且 AA 位是「透明度」而非
「不透明度」（00 完全不透明、FF 完全透明），与 RGBA 的 alpha 正好相反。
这两点各自反了一次，凭直觉写必错，所以单独收在这里。

弹幕与字幕的样式配置就是按这个格式存在 config.json 里的（见 schema.py 的
danmaku_style / subtitle_style），下游直接拼进 .ass 文件的 Style 行。

这里只用 (r, g, b, a) 元组，不碰 QColor —— 这条链路属于解析核心，WebUI 进程里没有 Qt。
桌面侧的 QColor 转换在 gui/component/setting/group.py 的边界上做。
"""

def ass_alpha_to_rgba(ass_str: str) -> tuple[int, int, int, int]:
    """`&HAABBGGRR` → (r, g, b, a)。a 是常规的不透明度，255 为完全不透明"""
    value = ass_str.lstrip("&H")

    a = int(value[0:2], 16)
    b = int(value[2:4], 16)
    g = int(value[4:6], 16)
    r = int(value[6:8], 16)

    return r, g, b, 255 - a

def rgba_to_ass_alpha(r: int, g: int, b: int, a: int) -> str:
    """(r, g, b, a) → `&HAABBGGRR`"""
    return f"&H{(255 - a):02X}{b:02X}{g:02X}{r:02X}"
