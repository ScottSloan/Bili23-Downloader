from util.common.enum import DownloadStatus, MetadataType
from util.download.task.info import TaskInfo
from util.parse.additional import metadata, metadata_refresh
from util.parse.episode.tree import Attribute

from urllib.parse import urlencode
from xml.etree import ElementTree
import json

import pytest


@pytest.fixture
def task(tmp_path):
    task = TaskInfo()
    task.Download.status = DownloadStatus.COMPLETED
    task.Episode.attribute = Attribute.VIDEO_BIT | Attribute.NORMAL_BIT
    task.Episode.bvid = "BVcurrent"
    task.Episode.description = "old"
    task.File.name = "original-filename"
    task.File.download_path = str(tmp_path)
    return task


@pytest.fixture
def api(monkeypatch):
    calls = []

    class Request:
        def __init__(self, url):
            self.url = url

        def run(self):
            calls.append(self.url)
            if "/tag?" in self.url:
                return {"code": 0, "data": [{"tag_name": "Art & design"}]}
            return {"code": 0, "data": {"bvid": "BVcurrent", "desc": "new & <updated>"}}

    monkeypatch.setattr(metadata, "SyncNetWorkRequest", Request)
    monkeypatch.setattr(metadata.MetadataParser, "enc_wbi", lambda self, params: urlencode(params))
    return calls


def run_refresh(tasks, format, batch_size = 1, pause = 0):
    worker = metadata_refresh.MetadataRefreshWorker(tasks, format, batch_size, pause)
    results = []
    worker.result.connect(lambda *args: results.append(args))
    worker.run()
    return results[0]


@pytest.mark.parametrize("format", [MetadataType.JSON, MetadataType.NFO])
def test_refresh_reuses_the_existing_filename_and_does_not_change_download_record(task, api, format, tmp_path):
    path = tmp_path / f"{task.File.name}.元数据.{format.value}"
    if format == MetadataType.JSON:
        path.write_text('{"bvid":"BVcurrent","description":"old"}', encoding = "utf-8")
    else:
        # 模拟以前的导出：XML 正文未转义，但仍可从 BV 标识确认归属。
        path.write_text('<movie><plot>old & invalid</plot><uniqueid type="bvid">BVcurrent</uniqueid></movie>', encoding = "utf-8")

    assert run_refresh([task], format) == (1, 0, "")
    assert list(tmp_path.iterdir()) == [path]
    if format == MetadataType.JSON:
        output = json.loads(path.read_text(encoding = "utf-8"))
        assert output["description"] == "new & <updated>"
        assert output["tags"] == ["Art & design"]
    else:
        output = ElementTree.parse(path)
        assert output.findtext("plot") == "new & <updated>"
        assert output.findtext("tag") == "Art & design"
    assert task.Episode.description == "old"
    assert task.Download.status == DownloadStatus.COMPLETED
    assert len(api) == 2


def test_refresh_leaves_mismatched_metadata_intact(task, api, tmp_path):
    path = tmp_path / f"{task.File.name}.Metadata.json"
    original = '{"bvid":"BVdifferent","description":"Do not replace"}'
    path.write_text(original, encoding = "utf-8")

    assert run_refresh([task], MetadataType.JSON)[:2] == (0, 1)
    assert path.read_text(encoding = "utf-8") == original


def test_failed_request_keeps_existing_file_and_stops_when_rate_limited(task, api, monkeypatch, tmp_path):
    path = tmp_path / f"{task.File.name}.Metadata.json"
    original = '{"bvid":"BVcurrent","description":"Keep this"}'
    path.write_text(original, encoding = "utf-8")

    class BlockedRequest:
        def __init__(self, url):
            api.append(url)

        def run(self):
            return {"code": -412, "message": "Request blocked"}

    monkeypatch.setattr(metadata, "SyncNetWorkRequest", BlockedRequest)
    assert run_refresh([task, task], MetadataType.JSON)[:2] == (0, 1)
    assert path.read_text(encoding = "utf-8") == original
    assert len(api) == 1


def test_refresh_can_stop_between_batches(task, api, tmp_path):
    worker = metadata_refresh.MetadataRefreshWorker([task, task], MetadataType.JSON, batch_size = 1, pause = 120)
    worker.progress.connect(lambda _: worker.cancel())
    results = []
    worker.result.connect(lambda *args: results.append(args))
    worker.run()

    assert results == [(1, 0, "")]
    assert len(api) == 2
    assert len(list(tmp_path.iterdir())) == 1
