"""
config.DefaultValue 的别名关系。

qfluentwidgets 的 ConfigItem 直接持有默认值对象本身，config.get() 在用户
没有自定义过该项时，返回的就是 DefaultValue 上那个 list / dict —— 不是副本。

    >>> config.get(config.video_quality_priority) is DefaultValue.video_quality_priority
    True

于是任何一处「拿到之后就地改」都会把进程内的默认值永久改掉：后续所有读取
都拿到被污染的值，重置设置也恢复不回来，而这中间没有任何报错。

「默认值全程未被修改」这条断言放在 conftest.py 的 pytest_sessionfinish 中，
因为它必须在整场测试结束后才有意义 —— 写成普通用例只能覆盖到它自己之前
发生的修改。本文件负责把别名关系本身记录下来。
"""

from util.common.config import DefaultValue, config


class TestAliasing:
    """记录这层别名关系本身，使其不至于被无意中依赖或遗忘"""

    def test_get_returns_the_default_object_itself(self):
        # 这不是期望的设计，而是 qfluentwidgets 的既有行为。
        # 一旦它哪天改成返回副本，上面那些 .copy() 就成了多余，本用例会提醒
        assert config.get(config.video_quality_priority) is DefaultValue.video_quality_priority

    def test_shallow_copy_does_not_protect_nested_structures(self):
        # danmaku_style / subtitle_style 都是嵌套字典，.copy() 只拷一层。
        # 现有代码只读取内层不修改，所以安全；这里把这个前提写明
        shallow = config.get(config.danmaku_style).copy()

        assert shallow is not DefaultValue.danmaku_style
        assert shallow["font"] is DefaultValue.danmaku_style["font"], (
            "内层字典仍是同一个对象 —— 若将来需要修改内层，必须改用 deepcopy"
        )
