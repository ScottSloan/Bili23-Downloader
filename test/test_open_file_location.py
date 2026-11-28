"""
只下载附加内容的任务「打开文件位置」误报找不到文件（Issue #507）。

「打开文件位置」原先只认 relative_files，而那份列表只登记音视频产物；附加内容的文件
从来不进去 —— 也不能进去，合并完成、取消任务时 relative_files 里的文件都会被当作
临时文件删掉，附加文件又恰好在合并之前生成。这里钉住：附加文件另记一份，
没有音视频产物时据此定位，有产物时表现不变。
"""

from util.common.enum import DownloadStatus
from util.download.task.info import TaskInfo


def make_task_info(tmp_path) -> TaskInfo:
    task_info = TaskInfo()
    task_info.File.download_path = str(tmp_path)
    task_info.File.folder = "folder"
    task_info.File.name = "video"

    return task_info


def test_write_registers_additional_file_once(tmp_path):
    from util.parse.additional.base import AdditionalParserBase

    task_info = make_task_info(tmp_path)
    parser = AdditionalParserBase(task_info)

    # 任务重试时附加内容会重新写一遍，同名文件不能重复登记
    parser._write("danmaku", suffix = "ass", qualifier = ["弹幕"])
    parser._write("danmaku", suffix = "ass", qualifier = ["弹幕"])
    parser._write(b"cover", suffix = "jpg")

    assert task_info.File.additional_files == ["video.弹幕.ass", "video.jpg"]
    # 不能混进 relative_files，否则合并完成后会被当作临时文件删掉
    assert task_info.File.relative_files == []


def test_locate_falls_back_to_additional_files(tmp_path):
    from gui.component.download_list.item_delegate import locate_output_files

    task_info = make_task_info(tmp_path)
    directory = tmp_path / "folder"
    directory.mkdir()

    (directory / "video.弹幕.ass").write_text("")
    task_info.File.additional_files = ["video.弹幕.ass", "video.jpg"]

    # 封面已被用户删掉，只选中仍然存在的文件
    assert locate_output_files(directory, task_info) == ["video.弹幕.ass"]


def test_locate_prefers_media_files(tmp_path):
    from gui.component.download_list.item_delegate import locate_output_files

    task_info = make_task_info(tmp_path)
    directory = tmp_path / "folder"
    directory.mkdir()

    (directory / "video.mp4").write_text("")
    (directory / "video.弹幕.ass").write_text("")
    task_info.File.relative_files = ["video.mp4", "video.m4a"]
    task_info.File.additional_files = ["video.弹幕.ass"]

    # 有音视频产物时只选中它们，与修复前的表现一致
    assert locate_output_files(directory, task_info) == ["video.mp4"]


def test_locate_returns_empty_when_nothing_exists(tmp_path):
    from gui.component.download_list.item_delegate import locate_output_files

    task_info = make_task_info(tmp_path)
    task_info.File.relative_files = ["video.mp4"]
    task_info.File.additional_files = ["video.弹幕.ass"]

    assert locate_output_files(tmp_path / "folder", task_info) == []


def test_old_task_data_without_additional_files(tmp_path):
    # 旧版本入库的任务数据里没有 additional_files 这一键，读回来应为空列表而不是报错
    task_info = make_task_info(tmp_path)
    data = task_info.to_dict()
    del data["File"]["additional_files"]

    restored = TaskInfo()
    restored.from_dict(data)

    assert restored.File.additional_files == []


def test_mcp_output_file_name_falls_back_to_additional_files(tmp_path):
    from util.mcp.tools.task import _output_file_name

    task_info = make_task_info(tmp_path)
    task_info.Download.status = DownloadStatus.COMPLETED
    task_info.File.additional_files = ["video.弹幕.ass"]

    assert _output_file_name(task_info) == "video.弹幕.ass"

    task_info.File.relative_files = ["video.mp4"]

    assert _output_file_name(task_info) == "video.mp4"
