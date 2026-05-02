from PySide6.QtWidgets import QFrame, QHBoxLayout, QVBoxLayout

from qfluentwidgets import SubtitleLabel, Pivot, PopUpAniStackedWidget

from gui.component.download_list import TopStackedWidget, DownloadListView
from gui.component.widget import PivotItem

from util.download import TaskInfo, QueryWorker
from util.common import signal_bus
from util.thread import AsyncTask

class DownloadInterface(QFrame):
    def __init__(self, parent = None):
        super().__init__(parent = parent)

        self.setObjectName("DownloadInterface")

        self.init_UI()

        self.get_tasks()

    def init_UI(self):
        self.pivot = Pivot(self)
        self.list_stacked_widget = PopUpAniStackedWidget(self)
        self.list_stacked_widget.setContentsMargins(0, 10, 0, 10)

        self.top_stacked_widget = TopStackedWidget(self)

        self.downloading_list_view = DownloadListView(self)
        self.downloading_list_view.setEmptyTextTip(self.tr("No downloads in progress"))
        self.downloading_list_view.setAutoManageConcurrentTasks(True)
        self.downloading_list_view.setAutoUpdateCountBadge(True)
        self.downloading_list_view.connectUpdateDataSignal()
        self.downloading_list_view.enableSorting("created_time")

        self.completed_list_view = DownloadListView(self)
        self.completed_list_view.setEmptyTextTip(self.tr("No completed downloads"))
        self.completed_list_view.enableSorting("completed_time")

        top_layout = QHBoxLayout()
        top_layout.addWidget(self.pivot)
        top_layout.addStretch()
        top_layout.addWidget(self.top_stacked_widget)

        self.addSubInterface(self.downloading_list_view, "downloading", self.tr("Downloading"), 0)
        self.addSubInterface(self.completed_list_view, "completed", self.tr("Completed"), 1)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(25, 15, 25, 15)
        main_layout.addLayout(top_layout)
        main_layout.addWidget(self.list_stacked_widget)

        self.pivot.setCurrentItem("downloading")

        self.connect_signals()

    def connect_signals(self):
        signal_bus.download.add_to_downloading_list.connect(self.downloading_list_view.addTask)
        signal_bus.download.add_to_completed_list.connect(self.completed_list_view.addTask)
        signal_bus.download.auto_manage_concurrent_downloads.connect(self.downloading_list_view._schedule_auto_manage_concurrent_downloads)

        signal_bus.download.remove_from_downloading_list.connect(self.downloading_list_view.removeTask)
        signal_bus.download.remove_from_completed_list.connect(self.completed_list_view.removeTask)

        signal_bus.download.sort_downloading_list.connect(self.downloading_list_view._model.sortBy)
        signal_bus.download.sort_completed_list.connect(self.completed_list_view._model.sortBy)

        self.top_stacked_widget.start_all_btn.clicked.connect(self.downloading_list_view._model.batchStart)
        self.top_stacked_widget.pause_all_btn.clicked.connect(self.downloading_list_view._model.batchPause)
        self.top_stacked_widget.delete_all_btn.clicked.connect(self.downloading_list_view.batch_cancel)
        
        self.top_stacked_widget.clear_all_btn.clicked.connect(self.completed_list_view._model.batch_cancel)

    def addSubInterface(self, widget: SubtitleLabel, objectName: str, text: str, index):
        def onClick():
            self.list_stacked_widget.setCurrentWidget(widget)
            self.top_stacked_widget.setCurrentIndex(index)

        widget.setObjectName(objectName)
        self.list_stacked_widget.addWidget(widget)

        item = PivotItem(text = text, parent = self.pivot)
        item.setMaximumWidth(150)
        item.setFontSize(15)

        item = self.pivot.insertWidget(-1, objectName, item, onClick)

    def get_tasks(self):
        # 从数据库中查询下载任务，并添加到列表中
        worker = QueryWorker()
        worker.success.connect(self.on_query_success)
        worker.error.connect(self.on_query_error)

        AsyncTask.run(worker)
    
    def on_query_success(self, downloading_tasks: list[TaskInfo], completed_tasks: list[TaskInfo]):
        self.downloading_list_view._beginAddQueriedTasks()

        self.downloading_list_view.addTask(downloading_tasks)
        self.completed_list_view.addTask(completed_tasks)

        self.downloading_list_view._endAddQueriedTasks()

    def on_query_error(self, error_message: str):
        signal_bus.toast.show_long_message.emit(self.tr("Failed to query download tasks"), error_message)
