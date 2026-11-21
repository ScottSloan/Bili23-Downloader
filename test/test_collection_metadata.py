"""合集的不同稿件应导出各自的简介，而不是入口稿件的共享简介（#498）。"""

from util.common.enum import MetadataType
from util.download.task.manager import task_manager
from util.parse.additional import metadata
from util.parse.episode.tree import Attribute, EpisodeData
from util.parse.episode.video import VideoEpisodeParser
from util.network.error import APIError

from urllib.parse import parse_qs, urlencode, urlparse
from xml.etree import ElementTree
import json

import pytest


@pytest.fixture
def collection_tasks(tmp_path):
    EpisodeData.clear_cache()
    episodes = []
    for index, bvid in enumerate(("BVentry", "BVother"), 1):
        episodes.append({
            "aid": index, "bvid": bvid, "cid": index * 10, "title": bvid,
            # 真实合集响应的 arc.desc 可能为空，不能当作完整简介。
            "arc": {"pic": "", "pubdate": 1700000000, "duration": 60, "desc": ""},
            "pages": [{"page": 1, "cid": index * 10, "part": "P1", "duration": 60}],
        })
    # 另一个稿件有两个分P，修复不能将单P下载变成整稿下载。
    episodes[1]["pages"].append({"page": 2, "cid": 21, "part": "P2", "duration": 70})
    response = {"data": {
        "bvid": "BVentry", "cid": 10, "desc": "入口视频的简介",
        "owner": {"name": "UP", "mid": 1, "face": ""},
        "ugc_season": {"title": "测试合集", "sections": [{"title": "正片", "episodes": episodes}]},
    }}
    tree = VideoEpisodeParser(response, "USER_UPLOADS").parse(update_episode_list = False)
    tasks = []
    for number, item in enumerate(tree.get_all_children(to_dict = True), 1):
        task = task_manager._TaskManager__episode_info_to_task_info(item, number, {
            "download_metadata": True, "download_video_stream": False, "download_audio_stream": False,
        })
        task.File.download_path = str(tmp_path)
        task.File.folder = ""
        task.File.name = f"{task.Episode.bvid}-{task.Episode.cid}"
        tasks.append(task)
    yield tasks
    EpisodeData.clear_cache()


@pytest.fixture
def metadata_api(monkeypatch):
    descriptions = {"BVentry": "入口视频的简介", "BVother": "另一个视频的简介"}
    requested = []

    class Request:
        def __init__(self, url):
            self.url = url

        def run(self):
            requested.append(self.url)
            query = parse_qs(urlparse(self.url).query)
            bvid = query["bvid"][0]
            if urlparse(self.url).path.endswith("/tag"):
                return {"code": 0, "data": [{"tag_name": "A & B"}, {"tag_name": None}]}
            return {"code": 0, "data": {"bvid": bvid, "desc": descriptions[bvid]}}

    monkeypatch.setattr(metadata, "SyncNetWorkRequest", Request)
    # 网络边界已替换，不依赖真实账号、签名密钥或网络。
    monkeypatch.setattr(metadata.MetadataParser, "enc_wbi", lambda self, params: urlencode(params))
    return descriptions, requested


@pytest.mark.parametrize("kind", [MetadataType.JSON, MetadataType.NFO])
def test_collection_exports_each_videos_description(collection_tasks, metadata_api, kind, tmp_path):
    descriptions, requested = metadata_api
    assert len(collection_tasks) == 3
    original_cids = [task.Episode.cid for task in collection_tasks]

    for task in collection_tasks:
        task.Options.metadata_type = kind.value
        metadata.MetadataParser(task).parse()
        path, = tmp_path.glob(f"{task.File.name}.*.{kind.value}")
        if kind == MetadataType.JSON:
            data = json.loads(path.read_text(encoding = "utf-8"))
            exported = data["description"]
            assert data["tags"] == ["A & B"]
        else:
            data = ElementTree.parse(path)
            exported = data.findtext("plot")
            assert data.findtext("tag") == "A & B"
        assert exported == descriptions[task.Episode.bvid]

    assert [task.Episode.cid for task in collection_tasks] == original_cids
    assert {parse_qs(urlparse(url).query)["bvid"][0] for url in requested} == set(descriptions)


@pytest.mark.parametrize("kind", [MetadataType.JSON, MetadataType.NFO])
def test_empty_description_does_not_keep_entry_description(collection_tasks, metadata_api, kind, tmp_path):
    descriptions, _ = metadata_api
    descriptions["BVother"] = ""
    task = collection_tasks[1]
    task.Options.metadata_type = kind.value
    metadata.MetadataParser(task).parse()
    path, = tmp_path.glob(f"{task.File.name}.*.{kind.value}")
    if kind == MetadataType.JSON:
        assert "description" not in json.loads(path.read_text(encoding = "utf-8"))
    else:
        assert ElementTree.parse(path).findtext("plot") == ""


@pytest.mark.parametrize("kind", [MetadataType.JSON, MetadataType.NFO])
def test_api_error_does_not_export_stale_description(collection_tasks, monkeypatch, kind, tmp_path):
    task = collection_tasks[1]
    task.Options.metadata_type = kind.value

    class FailedRequest:
        def __init__(self, url):
            pass

        def run(self):
            return {"code": -412, "message": "request blocked"}

    monkeypatch.setattr(metadata, "SyncNetWorkRequest", FailedRequest)
    monkeypatch.setattr(metadata.MetadataParser, "enc_wbi", lambda self, params: urlencode(params))
    with pytest.raises(APIError):
        metadata.MetadataParser(task).parse()
    assert not list(tmp_path.iterdir())


@pytest.mark.parametrize("attribute", [
    Attribute.VIDEO_BIT | Attribute.NORMAL_BIT,
    Attribute.VIDEO_BIT | Attribute.PART_BIT,
    Attribute.BANGUMI_BIT,
])
def test_other_video_types_do_not_request_description(collection_tasks, metadata_api, attribute):
    _, requested = metadata_api
    task = collection_tasks[0]
    task.Episode.attribute = attribute
    task.Options.metadata_type = MetadataType.JSON.value
    metadata.MetadataParser(task).parse()
    assert not any(urlparse(url).path.endswith("/wbi/view") for url in requested)


def test_export_recovers_a_description_missing_from_the_parse_cache(tmp_path, metadata_api):
    descriptions, _ = metadata_api
    response = {"data": {
        "bvid": "BVentry", "aid": 1, "cid": 10, "desc": descriptions["BVentry"],
        "title": "Standalone video", "pic": "", "pubdate": 1700000000, "is_upower_exclusive": False,
        "owner": {"name": "UP", "mid": 1, "face": ""},
    }}
    tree = VideoEpisodeParser(response, "USER_UPLOADS").parse(update_episode_list = False)
    item, = tree.get_all_children(to_dict = True)
    # 新一轮解析可能在异步建任务前清除旧缓存。
    EpisodeData.clear_cache()
    task = task_manager._TaskManager__episode_info_to_task_info(item, 1)
    assert not task.Episode.description
    task.File.download_path = str(tmp_path)
    task.File.folder = ""
    task.Options.metadata_type = MetadataType.JSON.value
    metadata.MetadataParser(task).parse()
    path, = tmp_path.glob("*.json")
    assert json.loads(path.read_text(encoding = "utf-8"))["description"] == descriptions["BVentry"]


def test_tag_request_failure_does_not_discard_available_json(collection_tasks, metadata_api, monkeypatch, tmp_path):
    request = metadata.SyncNetWorkRequest

    class UnavailableTags(request):
        def run(self):
            if urlparse(self.url).path.endswith("/tag"):
                return {"code": -404, "message": "Tags unavailable"}
            return super().run()

    monkeypatch.setattr(metadata, "SyncNetWorkRequest", UnavailableTags)
    task = collection_tasks[1]
    task.Options.metadata_type = MetadataType.JSON.value
    metadata.MetadataParser(task).parse()
    path, = tmp_path.glob("*.json")
    data = json.loads(path.read_text(encoding = "utf-8"))
    assert data["description"] == "另一个视频的简介"
    assert "tags" not in data
