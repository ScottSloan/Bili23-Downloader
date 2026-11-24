"""
合集条目导出的元数据（#498）。

合集里所有条目共用入口稿件的 episode_id，任务里带的简介是入口稿件那一份，导出 JSON/NFO 时
每一集都成了同一句简介。现在导出前按当前 BV 重新查一次。这里钉住三件事：
各条目拿到各自的简介；查询失败时留空而不是沿用入口稿件的简介，且不让已下载完成的任务失败；
NFO 中的简介、标签经过 XML 转义，含 < & 的简介不会写出损坏的文件。
"""

import httpx
import pytest

from xml.etree import ElementTree


DESCRIPTIONS = {"BVentry": "入口视频的简介", "BVother": "另一个视频的简介"}


@pytest.fixture
def metadata_api(monkeypatch):
    from util.parse.additional import metadata

    state = {"view": "ok", "tag": "ok", "requested": []}

    class FakeRequest:
        def __init__(self, url, *args, **kwargs):
            self.url = url

        def run(self):
            state["requested"].append(self.url)
            bvid = httpx.URL(self.url).params["bvid"]

            if "/view/detail/tag" in self.url:
                if state["tag"] == "risk_control":
                    request = httpx.Request("GET", self.url)
                    raise httpx.HTTPStatusError("412", request = request, response = httpx.Response(412, request = request))

                return {"code": 0, "data": [{"tag_name": "A & B"}, {"tag_name": None}, {"tag_name": "<标签>"}]}

            if state["view"] == "risk_control":
                return {"code": -412, "message": "请求被拦截"}

            return {"code": 0, "data": {"bvid": bvid, "desc": DESCRIPTIONS[bvid]}}

    monkeypatch.setattr(metadata, "SyncNetWorkRequest", FakeRequest)
    # 网络边界已替换，签名与本用例无关
    monkeypatch.setattr(metadata.MetadataParser, "enc_wbi", lambda self, params: f"bvid={params['bvid']}")

    return state


def make_task(tmp_path, bvid: str, metadata_type: str, collection: bool = True):
    from util.download.task.info import TaskInfo
    from util.parse.episode.tree import Attribute

    task = TaskInfo()
    task.Episode.bvid = bvid
    task.Episode.attribute = Attribute.VIDEO_BIT | (Attribute.COLLECTION_BIT if collection else 0)
    # 解析阶段写进任务的是入口稿件的简介，这正是 #498 的出错点
    task.Episode.description = DESCRIPTIONS["BVentry"]
    task.Options.metadata_type = metadata_type
    task.File.download_path = str(tmp_path)
    task.File.folder = ""
    task.File.name = bvid

    return task


def export(task):
    from util.parse.additional.metadata import MetadataParser

    MetadataParser(task).parse()


def read_json(tmp_path, bvid: str):
    from util.common._json import loads

    (path,) = tmp_path.glob(f"{bvid}.*.json")

    return loads(path.read_text(encoding = "utf-8"))


def test_collection_items_use_their_own_description(tmp_path, metadata_api):
    for bvid in ("BVentry", "BVother"):
        export(make_task(tmp_path, bvid, "json"))

    assert read_json(tmp_path, "BVentry")["description"] == "入口视频的简介"
    assert read_json(tmp_path, "BVother")["description"] == "另一个视频的简介"
    # JSON 也带上标签（#494），空值被滤掉
    assert read_json(tmp_path, "BVother")["tags"] == ["A & B", "<标签>"]


def test_description_lookup_failure_leaves_it_empty(tmp_path, metadata_api):
    metadata_api["view"] = "risk_control"

    # 被风控拦下也不能抛出去，否则已下载完成的任务会整个判为失败
    export(make_task(tmp_path, "BVother", "json"))

    # 宁缺也不能写入入口稿件的简介；空值在导出时被滤掉
    assert "description" not in read_json(tmp_path, "BVother")


def test_tag_lookup_failure_still_exports(tmp_path, metadata_api):
    metadata_api["tag"] = "risk_control"

    export(make_task(tmp_path, "BVother", "json"))

    assert read_json(tmp_path, "BVother")["description"] == "另一个视频的简介"


def test_non_collection_keeps_parsed_description(tmp_path, metadata_api):
    # 普通稿件解析时拿到的就是自己的简介，不必多发一次详情请求
    export(make_task(tmp_path, "BVentry", "json", collection = False))

    assert not any("/wbi/view" in url for url in metadata_api["requested"])
    assert read_json(tmp_path, "BVentry")["description"] == "入口视频的简介"


def test_nfo_is_valid_xml(tmp_path, metadata_api, monkeypatch):
    from util.parse.additional import metadata

    def description_with_markup(self):
        self.task_info.Episode.description = "a < b & c"

    monkeypatch.setattr(metadata.MetadataParser, "_get_video_description", description_with_markup)
    # 海报下载与本用例无关
    monkeypatch.setattr(metadata.MetadataParser, "_save_poster", lambda self: None)

    export(make_task(tmp_path, "BVother", "nfo"))

    (path,) = tmp_path.glob("*.nfo")
    root = ElementTree.parse(path).getroot()

    assert root.findtext("plot") == "a < b & c"
    assert [tag.text for tag in root.iter("tag")] == ["A & B", "<标签>"]
