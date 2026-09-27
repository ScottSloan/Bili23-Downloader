"""
util/download/task/reparse_worker.py —— 二次解析的分派与失败契约。

标了 NEED_PARSE_BIT 的条目（收藏夹、个人空间、历史记录、稍后再看、合集列表里
的每一条）都要经这里再解析一次，按媒体形态位选一个 parser 出来。

分派依赖「每个来源解析器都会给出一个形态位」这条约定。约定被破坏时这里曾经
没有分支：episode_parser 未绑定，UnboundLocalError 被 run() 的 except 原样塞进
提示框 —— 用户看到的是「局部变量 episode_parser 未绑定」，一句对定位毫无帮助的
Python 内部信息。历史记录的 business 加新取值就会踩中，那里也确实踩中过。

所以这里钉住的是失败**形态**：认不出的条目要抛 RuntimeError 带一句人话，
而不是让一个未绑定变量把真正的病因盖掉。
"""

from util.download.task.reparse_worker import ReparseWorker
from util.parse.episode.tree import Attribute

import pytest


class TestUnknownEntryType:
    def test_reports_a_real_message_instead_of_unbound_local(self):
        worker = ReparseWorker({"attribute": Attribute.NEED_PARSE_BIT})

        # UnboundLocalError 是 NameError 的子类，不会被 pytest.raises(RuntimeError)
        # 收下，所以这一条同时钉住了「有分支」与「抛的是 RuntimeError」
        with pytest.raises(RuntimeError) as error:
            worker.parse_episode_node_info()

        assert str(error.value).strip()
