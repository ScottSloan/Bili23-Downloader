from util.download.task.info import TaskInfo


def test_old_record_and_verification_round_trip():
    old = TaskInfo()
    old.from_dict({"File": {"name": "old"}})
    assert old.File.verification == {}
    old.File.verification = {"files": [{"status": "verified", "duration": 12.5}]}
    restored = TaskInfo()
    restored.from_dict(old.to_dict())
    assert restored.File.verification == old.File.verification


def test_verification_only_updates_existing_completed_record(tmp_path, monkeypatch):
    from util.download.task import db
    monkeypatch.setattr(db, "appdata_path", str(tmp_path))
    database = db.TaskDatabase()
    task = TaskInfo()
    task.Basic.task_id = "inspection"
    database.add_tasks([task], completed=True)
    result = {"files": [{"status": "verified"}]}
    database.save_verification(task.Basic.task_id, result)
    from util.common._json import loads
    raw = database.query("SELECT data FROM completed_task WHERE task_id = ?", (task.Basic.task_id,))[0][0]
    assert loads(raw)["File"]["verification"] == result
    database.delete_task(task.Basic.task_id, completed=True)
    database.save_verification(task.Basic.task_id, result)
    assert database.count_tasks(completed=True) == 0
    database.close_connection()


def test_inspection_dialog_cancel():
    from PySide6.QtWidgets import QApplication
    app = QApplication.instance() or QApplication([])
    from gui.dialog.misc.media_inspection import MediaInspectionDialog
    dialog = MediaInspectionDialog(TaskInfo())
    assert app is not None
    assert not dialog.cancel.is_set()
    dialog.reject()
    assert dialog.cancel.is_set()


def test_dialog_background_inspection_and_save(tmp_path, monkeypatch):
    from PySide6.QtWidgets import QApplication
    from PySide6.QtCore import QEventLoop, QTimer
    from gui.dialog.misc import media_inspection as module
    from util.media_probe import ProbeResult
    app = QApplication.instance() or QApplication([])
    task = TaskInfo()
    task.Basic.task_id = "background-check"
    task.File.download_path = str(tmp_path)
    task.File.relative_files = ["sample.mp4", "cover.jpg"]
    from util.common.enum import DownloadType
    task.Download.type = DownloadType.VIDEO | DownloadType.AUDIO
    task.Download.merge_video_audio = True
    calls = []
    expectations = []
    def probe(*args, **kwargs):
        expectations.append(kwargs)
        return ProbeResult(status="verified", duration=10)
    monkeypatch.setattr(module, "probe_media", probe)
    from concurrent.futures import Future
    def save(*args):
        calls.append(args)
        future = Future()
        future.set_result(None)
        return future
    monkeypatch.setattr(module.task_manager, "save_verification", save)
    dialog = module.MediaInspectionDialog(task)
    dialog.startInspection()
    loop = QEventLoop()
    timer = QTimer()
    timer.timeout.connect(lambda: loop.quit() if dialog.inspect.isEnabled() else None)
    timer.start(10)
    QTimer.singleShot(2000, loop.quit)
    loop.exec()
    timer.stop()
    assert app is not None
    assert dialog.inspect.isEnabled()
    assert expectations[0]["expect_video"] is True
    assert expectations[0]["expect_audio"] is True
    assert calls[0][0] == task.Basic.task_id
    assert len(calls[0][1]["files"]) == 1
    assert "10" in dialog.output.toPlainText()
    dialog.reject()


def test_worker_reports_probe_exception(tmp_path, monkeypatch):
    from gui.dialog.misc import media_inspection as module
    from threading import Event
    def fail(*args, **kwargs):
        raise OSError("temporary storage failure")
    monkeypatch.setattr(module, "probe_media", fail)
    worker = module.InspectionWorker([(tmp_path / 'x.mp4', {})], None, Event(), 'x')
    results, finished = [], []
    worker.result.connect(results.append)
    worker.finished.connect(lambda: finished.append(True))
    worker.run()
    assert results[0]['reason'] == 'inspection_error'
    assert finished == [True]


def test_worker_reports_save_failure_and_keeps_results(tmp_path, monkeypatch):
    from gui.dialog.misc import media_inspection as module
    from util.media_probe import ProbeResult
    from threading import Event
    from concurrent.futures import Future
    monkeypatch.setattr(module, 'probe_media', lambda *a, **kw: ProbeResult(status='verified'))
    future = Future()
    future.set_exception(OSError('database unavailable'))
    monkeypatch.setattr(module.task_manager, 'save_verification', lambda *a: future)
    worker = module.InspectionWorker([(tmp_path / 'x.mp4', {})], None, Event(), 'x')
    results = []
    worker.result.connect(results.append)
    worker.run()
    assert results[0]['saved'] is False
    assert results[0]['files'][0]['status'] == 'verified'


def test_inspection_translations():
    from pathlib import Path
    from PySide6.QtCore import QTranslator
    for language in ("zh_CN", "zh_TW"):
        translator = QTranslator()
        assert translator.load(str(Path(__file__).parents[1] / "src/res/i18n" / f"bili23.{language}.qm"))
        assert translator.translate("MediaInspectionDialog", "Results saved")
        assert translator.translate("DownloadListView", "Inspect media")
