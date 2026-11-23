"""
批量解析（贴一组 av/BV 链接）的剧集树构建（#497）。

链接指向的稿件属于某个合集时，单链接解析会列出整个合集再定位到目标；批量模式没有定位这一步，
开着"自动加入下载列表"时会把每条链接所在的整个合集都送进下载队列。这里钉住两件事：
每条链接只产出它自己那个稿件的条目，且不同链接不共用同一份剧集数据。
"""

import pytest

from types import SimpleNamespace


def make_episode(bvid: str, cids: list):
    return {
        "aid": cids[0], "bvid": bvid, "cid": cids[0], "title": bvid,
        "arc": {"pic": "", "pubdate": 1700000000, "duration": 60, "desc": ""},
        "pages": [{"page": index, "cid": cid, "part": f"P{index}", "duration": 60} for index, cid in enumerate(cids, 1)],
    }


def make_view_response(bvid: str, desc: str, uploader: str, episodes: list):
    # 精简过的 x/web-interface/view 响应：稿件本身属于一个单章节的合集
    target = next(episode for episode in episodes if episode["bvid"] == bvid)

    return {"data": {
        "aid": target["aid"], "bvid": bvid, "cid": target["cid"], "title": bvid, "pic": "", "pubdate": 1700000000,
        "desc": desc, "is_upower_exclusive": False, "pages": target["pages"],
        "owner": {"name": uploader, "mid": 1, "face": ""},
        "ugc_season": {"title": f"{uploader} 的合集", "sections": [{"title": "正片", "episodes": episodes}]},
    }}


@pytest.fixture
def batch_parser(monkeypatch):
    from util.common.enum import ParserType
    from util.common.signal_bus import signal_bus
    from util.parse.episode import download_history, dynamic
    from util.parse.episode.dynamic import DynamicEpisodeParser
    from util.parse.episode.tree import EpisodeData

    created = []
    appended = []

    # 下载记录要查库，与这里要验证的建树逻辑无关
    monkeypatch.setattr(download_history, "mark_download_history", lambda nodes: None)
    monkeypatch.setattr(dynamic, "mark_download_history", lambda nodes: None)
    # 打开"自动加入下载列表"，并把建任务改成同步记录，直接看送进下载队列的是哪些条目
    monkeypatch.setattr(dynamic, "config", SimpleNamespace(get = lambda item: True, auto_add_to_download_list = None))
    monkeypatch.setattr(dynamic.GlobalThreadPoolTask, "run_func", lambda func, items, *args: created.extend(items))

    def on_append(nodes):
        appended.extend(nodes)

    signal_bus.parse.append_parse_list_nodes.connect(on_append)

    with EpisodeData.parsing():
        parser = DynamicEpisodeParser({}, "USER_UPLOADS")
        parser.init_episode_parser(ParserType.VIDEO)

        yield parser, created, appended

    signal_bus.parse.append_parse_list_nodes.disconnect(on_append)


def leaf_bvids(nodes):
    return [leaf.bvid for node in nodes for leaf in node.get_all_leaves()]


def test_only_linked_videos_are_kept(batch_parser):
    parser, created, appended = batch_parser

    # 两个链接各属于一个合集；BVmulti 有两个分P，必须完整保留
    first_collection = [make_episode("BVa1", [11]), make_episode("BVsingle", [12]), make_episode("BVa3", [13])]
    second_collection = [make_episode("BVb1", [21]), make_episode("BVmulti", [22, 23]), make_episode("BVb3", [24])]

    parser.update_link_node(make_view_response("BVsingle", "单P的简介", "UP 甲", first_collection))
    parser.update_link_node(make_view_response("BVmulti", "分P的简介", "UP 乙", second_collection))

    assert leaf_bvids(appended) == ["BVsingle", "BVmulti", "BVmulti"]
    assert [item["bvid"] for item in created] == ["BVsingle", "BVmulti", "BVmulti"]
    assert [item["cid"] for item in created] == [12, 22, 23]


def test_links_do_not_share_episode_data(batch_parser):
    from util.parse.episode.tree import EpisodeData

    parser, created, appended = batch_parser

    parser.update_link_node(make_view_response("BVsingle", "单P的简介", "UP 甲", [make_episode("BVsingle", [12])]))
    parser.update_link_node(make_view_response("BVmulti", "分P的简介", "UP 乙", [make_episode("BVmulti", [22, 23])]))

    first, *rest = created

    # 复用同一个 episode_id 时，第二条链接的简介与 UP 主会把第一条的覆盖掉
    assert all(item["episode_id"] != first["episode_id"] for item in rest)
    assert EpisodeData.get_episode_data(first["episode_id"])["description"] == "单P的简介"
    assert EpisodeData.get_episode_data(first["episode_id"])["uploader"] == "UP 甲"
    assert EpisodeData.get_episode_data(rest[0]["episode_id"])["description"] == "分P的简介"
