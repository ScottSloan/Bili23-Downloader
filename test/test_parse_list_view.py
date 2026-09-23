"""
gui/component/parse_list/tree_view.py —— 解析列表对"链接指向的视频"的定位。

合集播放页链接（www.bilibili.com/list/{mid}?oid=…&bvid=…）指向合集里的某一集，
解析列表据此自动勾选并滚动过去。这一集未必落在解析的第一页里 —— 合集按发布时间
排序，链接指向的那一集完全可能在后面的页上，而分页是一页一个信号追加进列表的，
首屏那次定位自然找不到它。

定位只发生在信号抵达时，没有事件循环驱动就不会重来，所以这里直接构造控件、
按分页的顺序喂节点，断言目标出现在后一页时仍会被勾选。
"""

from PySide6.QtWidgets import QApplication, QWidget

from util.parse.episode.tree import Attribute, TreeItem

import pytest


@pytest.fixture(scope = "module")
def app():
    instance = QApplication.instance() or QApplication([])

    import res.resources_rc   # noqa: F401  图标与样式表由此注册，构造控件时会用到

    return instance


@pytest.fixture
def parent(app):
    return QWidget()


def make_item(bvid: str):
    item = TreeItem({"bvid": bvid, "title": bvid})

    return item


def make_page(bvids: list):
    """一页解析结果：外层包装节点 → 合集节点 → 条目，与信号里传的结构一致"""
    root = TreeItem({})

    node = TreeItem({"number": "合集列表", "title": "测试合集"})
    node.set_attribute(Attribute.TREE_NODE_BIT)

    for bvid in bvids:
        node.add_child(make_item(bvid))

    root.add_child(node)

    return root


def make_view(parent):
    from gui.component.parse_list.tree_view import ParseTreeView

    # main_window 只在悬停、右键菜单里用到，定位路径不碰它
    return ParseTreeView(None, parent)


def test_target_on_the_first_page_is_checked_immediately(parent):
    view = make_view(parent)

    view.update_tree(make_page(["BV_target", "BV_other"]), ("bvid", "BV_target"))

    assert [item.bvid for item in view.get_checked_items()] == ["BV_target"]
    assert view._pending_episode_data is None


def test_target_on_a_later_page_is_checked_when_it_arrives(parent):
    view = make_view(parent)

    view.update_tree(make_page(["BV_first", "BV_second"]), ("bvid", "BV_target"))

    assert view.get_checked_items() == [], "第一页里没有目标，不该勾选任何条目"
    assert view._pending_episode_data == ("bvid", "BV_target"), "要把定位信息留着等后续分页"

    view.append_nodes([make_item("BV_target")])

    assert [item.bvid for item in view.get_checked_items()] == ["BV_target"]
    assert view._current_episode_item.bvid == "BV_target", "媒体信息预览要指向这一项"
    assert view._pending_episode_data is None, "定位到了就不该再留着"


def test_pending_target_is_dropped_when_a_new_parse_starts(parent):
    view = make_view(parent)

    view.update_tree(make_page(["BV_first"]), ("bvid", "BV_target"))
    view.clear_tree()

    assert view._pending_episode_data is None

    # 上一次没找到的目标不该在这一棵树里被勾上
    view.append_nodes([make_item("BV_target")])

    assert view.get_checked_items() == []


def test_no_locate_data_means_no_checking(parent):
    # 个人空间、收藏夹这类链接不指向具体条目，追加分页时也不能凭空勾选
    view = make_view(parent)

    view.update_tree(make_page(["BV_first"]))
    view.append_nodes([make_item("BV_second")])

    assert view.get_checked_items() == []
